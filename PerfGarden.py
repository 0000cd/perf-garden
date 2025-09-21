import concurrent.futures
import csv
import os
import queue
import re
import threading
import time

import cv2  # pip install opencv-python
import numpy as np  # pip install numpy
import yaml  # pip install pyyaml


# 猫尾草：图片模板匹配，按钮标题等查找静态首尾帧
def cattail(
    img_path: str, template_path: str, threshold: float = 0.9, crop: int = 0
) -> tuple:
    """
    模板匹配检测函数（支持区域裁剪）

    参数：
    img_path: 待检测图片路径
    template_path: 模板图片路径
    threshold: 匹配阈值 (0~1)
    crop: 裁剪比例 (-99~99)
          >0 从底部向上裁剪，保留底部
          <0 从顶部向下裁剪，保留顶部
          =0 不裁剪

    返回：
    (status, matched, confidence, duration)
    """
    start_time = time.time()

    # 参数校验
    if not (0 <= threshold <= 1) or not (-99 <= crop <= 99):
        duration = round(time.time() - start_time, 2)
        return ("EC01", False, 0.00, duration)

    # 安全读取图片
    def _safe_read(path):
        try:
            return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        except:
            return None

    img = _safe_read(img_path)
    template = _safe_read(template_path)

    # 读取失败判断
    if img is None or template is None:
        duration = round(time.time() - start_time, 2)
        return ("EC02", False, 0.00, duration)

    # 执行裁剪操作
    if crop != 0:
        h, w = img.shape[:2]
        if crop > 0:
            # 保留底部区域
            new_h = max(1, int(h * (100 - crop) / 100))
            img = img[h - new_h: h, :]
        else:
            # 保留顶部区域
            new_h = max(1, int(h * abs(crop) / 100))
            img = img[0:new_h, :]

    # 模板尺寸校验
    if (template.shape[0] > img.shape[0]) or (template.shape[1] > img.shape[1]):
        duration = round(time.time() - start_time, 2)
        return ("EC03", False, 0.00, duration)

    # 灰度转换
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    # 执行匹配
    result = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)

    # 精度处理
    confidence = round(float(max_val), 2)
    duration = round(time.time() - start_time, 2)
    status = "PASS"
    matched = confidence >= threshold

    return (status, matched, confidence, duration)

# 仙人掌：图片差异区域占比，容忍局部加载动画，到开始输出文字气泡
def cactus(
    img_path: str, template_path: str, threshold: float = 1.0, crop: int = 0, enable_denoising: bool = False, acceleration: int = 2
) -> tuple:
    """
    图像差异检测函数（支持区域裁剪、加速和降噪控制）

    参数：
    img_path: 待检测图片路径
    template_path: 模板图片路径（用于对比的基准图片）
    threshold: 差异百分比阈值 (0~100)，默认为1%
    crop: 裁剪比例 (-99~99)
          >0 从底部向上裁剪，保留底部
          <0 从顶部向下裁剪，保留顶部
          =0 不裁剪
    enable_denoising: 是否启用降噪处理，默认关闭
    acceleration: 加速倍数 (1=原始, 2=2倍加速, 4=4倍加速)，默认2倍

    返回：
    (status, matched, confidence, duration)
    status: 状态码 ("PASS"/"EC01"/"EC02"/"EC03")
    matched: 是否检测到变化 (True/False)
    confidence: 差异百分比（置信度）
    duration: 执行耗时
    """
    start_time = time.time()

    # 参数校验
    if not (0 <= threshold <= 100) or not (-99 <= crop <= 99) or acceleration not in [1, 2, 4]:
        duration = round(time.time() - start_time, 4)
        return ("EC01", False, 0.00, duration)

    # 安全读取图片
    def _safe_read_grayscale(path):
        try:
            return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        except:
            return None

    img1 = _safe_read_grayscale(img_path)
    img2 = _safe_read_grayscale(template_path)

    # 读取失败判断
    if img1 is None or img2 is None:
        duration = round(time.time() - start_time, 4)
        return ("EC02", False, 0.00, duration)

    # 执行裁剪操作
    if crop != 0:
        h, w = img1.shape[:2]
        if crop > 0:
            # 保留底部区域
            new_h = max(1, int(h * (100 - crop) / 100))
            img1 = img1[h - new_h: h, :]
        else:
            # 保留顶部区域
            new_h = max(1, int(h * abs(crop) / 100))
            img1 = img1[0:new_h, :]
            
        # 对模板图片执行相同裁剪
        h2, w2 = img2.shape[:2]
        if crop > 0:
            # 保留底部区域
            new_h2 = max(1, int(h2 * (100 - crop) / 100))
            img2 = img2[h2 - new_h2: h2, :]
        else:
            # 保留顶部区域
            new_h2 = max(1, int(h2 * abs(crop) / 100))
            img2 = img2[0:new_h2, :]

    # 图像尺寸校验
    if img1.shape != img2.shape:
        duration = round(time.time() - start_time, 4)
        return ("EC03", False, 0.00, duration)

    # 下采样加速
    if acceleration > 1:
        new_h, new_w = img1.shape[0] // acceleration, img1.shape[1] // acceleration
        img1 = cv2.resize(img1, (new_w, new_h), interpolation=cv2.INTER_AREA)
        img2 = cv2.resize(img2, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # 计算绝对差异并二值化
    abs_diff = cv2.absdiff(img1, img2)
    _, diff_mask = cv2.threshold(abs_diff, 3, 255, cv2.THRESH_BINARY)

    # 可选的降噪处理
    if enable_denoising:
        kernel = np.ones((2, 2), np.uint8)
        diff_mask = cv2.morphologyEx(diff_mask, cv2.MORPH_OPEN, kernel)

    # 计算变化百分比
    changed_percentage = np.count_nonzero(diff_mask) / diff_mask.size * 100
    confidence = round(changed_percentage, 2)

    # 判断是否超过阈值
    matched = confidence >= threshold
    
    duration = round(time.time() - start_time, 4)
    status = "PASS"

    return (status, matched, confidence, duration)


# 三叶草：图片模板匹配

def blover(img_path, template_path=None, threshold: int = 1, crop: int = 0):
    """
    模板匹配检测函数（支持区域裁剪）

    参数：
    img_path: 待检测图片路径
    threshold: 匹配圆数量（正整数）
    crop: 裁剪比例 (-99~99)
          >0 从底部向上裁剪，保留底部
          <0 从顶部向下裁剪，保留顶部
          =0 不裁剪

    返回：
    (status（正常返回PASS）, matched（True/False，圆数量是否等于threshold）, confidence（检测到的圆圈数量）, duration)
    """
    start_time = time.time()

    # 参数检查
    if not isinstance(threshold, int) or threshold <= 0:
        return ("EB01", False, 0, time.time() - start_time)

    if not isinstance(crop, int) or crop < -99 or crop > 99:
        return ("EB01", False, 0, time.time() - start_time)

    # 安全读取图片为灰度图
    try:
        gray = cv2.imdecode(np.fromfile(
            img_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            return ("EB02", False, 0, time.time() - start_time)
    except Exception as e:
        return ("EB02", False, 0, time.time() - start_time)

    # 执行裁剪
    if crop != 0:
        h, w = gray.shape[:2]
        if crop > 0:
            # 保留底部区域
            new_h = max(1, int(h * (100 - crop) / 100))
            gray = gray[h - new_h: h, :]
        else:
            # 保留顶部区域
            new_h = max(1, int(h * abs(crop) / 100))
            gray = gray[0:new_h, :]

    # 预处理以减少噪声
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # 应用霍夫圆变换
    circlEB = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1,           # 图像分辨率与累加器分辨率之比（1:1保持原始分辨率，值越大检测越粗糙）
        minDist=100,    # 圆心间最小距离（防止重叠圆检测，需根据目标间距调整）
        param1=90,     # Canny边缘检测高阈值（值越大边缘检测要求越严格，建议50-150）
        param2=32,      # 圆心累加器阈值（值越小检测越宽松，假圆越多，建议10-50）
        minRadius=20,   # 目标最小半径（根据实际目标尺寸设置下限）
        maxRadius=25    # 目标最大半径（根据实际目标尺寸设置上限）
    )

    # 计算结果
    confidence = 0
    if circlEB is not None:
        confidence = len(circlEB[0])

    # 判断是否匹配
    # matched = confidence == threshold
    matched = confidence >= threshold

    duration = time.time() - start_time

    return ("PASS", matched, confidence, duration)


# 核心逻辑调度
def trails(
    image_files,
    folder_path,
    template_path=None,
    threshold=None,  # Changed from 0.8 to None
    leap=3,
    fade=False,
    crop=0,
    detector_func=None,  # New parameter to specify which detector function to use
):
    """
    处理提供的图片列表，通过设置跳跃间隔进行模板匹配检查

    参数:
        image_files: 已排序的图片文件名列表
        folder_path: 图片文件夹路径
        template_path: 模板图片路径
        threshold: 匹配阈值，默认为None，使用检测器函数的默认值
        leap: 检查间隔，默认为2，即每隔一张图片检查一次
        fade: 是否在匹配后继续进展直到匹配消失，默认为False
              - 当fade=False时，返回首个匹配成功的图片
              - 当fade=True时，返回匹配消失时的图片
        crop: 图像裁剪比例，默认为50
        detector_func: 检测器函数，默认为None时使用cattail

    返回值:
        元组 (status, matched_file, result):
        - status: 状态码，可能值为 "PASS"(成功)、"ERROR"(错误)、"UNFOUND"(未找到匹配)
        - matched_file: 匹配的文件名，如果未匹配则为None
        - result: 检测函数的原始返回结果，未找到匹配时为None
    """
    start_time = time.time()

    # 如果未指定检测器函数，默认使用cattail
    if detector_func is None:
        detector_func = cattail

    # 仙人掌特殊处理：如果没有模板且是cactus函数，使用第一张图片作为模板
    if detector_func == cactus and template_path is None and len(image_files) > 0:
        template_path = os.path.join(folder_path, image_files[0])
        print(f"🌵【cactus】使用第一张图片作为模板: {image_files[0]}")

    i = leap - 1  # 起始索引（对应第leap张图片）
    waiting_for_fade = False  # 是否在等待匹配消失
    first_match = None  # 第一个匹配的图片
    result_found = False  # 是否找到结果
    result = None  # 初始化result变量

    trails_status = "PASS"  # 返回状态
    trails_matched = None  # 返回文件名

    while i < len(image_files):
        img_file = image_files[i]
        img_path = os.path.join(folder_path, img_file)

        # 准备调用检测器函数的参数
        detector_kwargs = {
            "img_path": img_path,
            "template_path": template_path,
            "crop": crop,
        }

        # 只有在明确提供threshold时才传递
        if threshold is not None:
            detector_kwargs["threshold"] = threshold

        result = detector_func(**detector_kwargs)  # 使用指定的检测函数
        print(f"{img_file}: {result}")  # 🧐 详细调试日志

        # 解包结果元组
        status, matched, confidence, duration = result

        # 验证status，如果不是PASS则结束任务
        if status != "PASS":
            # print(f"\n任务结束，错误代码: {status}")
            trails_status = "ERROR"
            return (trails_status, trails_matched, result)

        if leap == 1:  # 在逐个检查模式
            if waiting_for_fade:  # 已经找到匹配，等待消失
                if not matched:  # 匹配消失
                    # print(f"\n在 {img_file} 消失")
                    result_found = True
                    trails_matched = img_file
                    break
            elif matched:  # 找到匹配
                if not fade:  # 标准模式，找到匹配就结束
                    # print(f"\n在 {img_file} 出现")
                    result_found = True
                    trails_matched = img_file
                    break
                else:  # fade模式，记录并继续
                    waiting_for_fade = True
                    first_match = img_file
        else:  # 在跳跃模式
            if matched:
                # 回退并开始逐个检查
                i = max(0, i - (leap - 1))  # 回退leap-1张图片
                # print(f"匹配成功，回退到 {image_files[i]} 开始逐个检查")
                leap = 1  # 设置步长为1
                continue

        i += leap  # 继续检查

    # 如果所有都没有找到结果，输出UNFOUND
    if not result_found:
        # print("\nUNFOUND")
        trails_status = "UNFOUND"
        result = None
        return (trails_status, trails_matched, result)

    # 输出总耗时
    total_duration = time.time() - start_time
    # print(f"\n总耗时: {total_duration:.2f} 秒")
    return (trails_status, trails_matched, result)


def gate_from_yaml(yaml_path, max_threads=None):
    """
    从YAML文件读取配置并处理文件夹

    参数:
        yaml_path: YAML配置文件路径
        max_threads: 最大线程数，如果为None则从YAML配置中读取或使用默认值

    返回:
        处理结果列表
    """
    # 读取YAML配置
    with open(yaml_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # 提取路径和任务信息
    parent_folder = None
    tasks = []
    task_headers = []
    task_type_counts = {}

    for item in config:
        if not isinstance(item, dict):
            continue

        # 提取母文件夹路径
        if "path" in item:
            parent_folder = os.path.normpath(item["path"])
            continue

        # 提取最大线程数
        if "max_threads" in item and max_threads is None:
            max_threads = item["max_threads"]
            continue

        # 提取任务信息
        for task_type, task_config in item.items():
            if task_type in ("path", "max_threads"):
                continue

            # 更新任务类型计数和表头
            task_type_counts[task_type] = task_type_counts.get(
                task_type, 0) + 1
            task_headers.append(f"{task_type}{task_type_counts[task_type]}")

            # 提取任务参数
            task_kwargs = {"task_type": task_type}
            if task_type == "skip":
                # 对于skip指令，直接存储要跳过的图片数
                task_kwargs["skip_count"] = task_config
            else:
                # 检测使用的是旧版格式还是新版格式
                if isinstance(task_config, list):
                    # 旧版格式: task_config 是一个参数字典的列表
                    for param in task_config:
                        for key, value in param.items():
                            if key == "template":
                                task_kwargs["template_path"] = os.path.normpath(
                                    value)
                            else:
                                task_kwargs[key] = value
                elif isinstance(task_config, dict):
                    # 新版格式: task_config 是一个字典
                    for key, value in task_config.items():
                        if key == "template":
                            task_kwargs["template_path"] = os.path.normpath(
                                value)
                        else:
                            task_kwargs[key] = value
                elif task_config is None:
                    # 处理无参数格式: task_config 是 None（如 "- cactus"）
                    pass  # 无需添加额外参数，使用默认参数
                else:
                    # 其他未知格式，记录警告
                    print(f"⚠️【警告】未知的任务配置格式: {task_type} = {task_config}，将使用默认参数")

            tasks.append(task_kwargs)

    if not parent_folder:
        raise ValueError("YAML配置中未指定母文件夹路径")

    if not tasks:
        tasks = [{}]
        task_headers = ["default1"]

    # 如果未指定最大线程数，使用默认值
    if max_threads is None:
        max_threads = os.cpu_count() or 4  # 默认使用CPU核心数

    # 执行任务处理
    return gate_multi_thread(parent_folder, tasks, task_headers, max_threads)


def process_subfolder(subfolder, tasks, csv_filename, csv_queue):
    """
    处理单个子文件夹的所有任务，在单独线程中执行

    参数:
        subfolder: 子文件夹路径
        tasks: 任务参数列表
        csv_filename: CSV结果文件路径
        csv_queue: 用于异步写入的队列

    返回:
        (subfolder_name, subfolder_results, total_time): 处理结果和耗时
    """
    subfolder_name = os.path.basename(subfolder)
    subfolder_results = []
    csv_row = [subfolder_name]
    total_time = 0

    # 获取并自然排序图片文件
    image_files = [
        f
        for f in os.listdir(subfolder)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif"))
    ]
    image_files.sort(
        key=lambda s: [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", s)
        ]
    )

    # 初始化剩余图片列表
    remaining_files = image_files.copy()

    # 执行每个任务
    for task_idx, task_kwargs in enumerate(tasks):
        if not remaining_files:
            print(f"🟠【警告】子文件夹 {subfolder_name}: 没有剩余图片，跳过剩余任务")
            csv_row.append("未执行")
            continue

        # 检查是否为跳过操作
        if task_kwargs.get("task_type") == "skip":
            skip_count = task_kwargs.get("skip_count", 0)
            if skip_count > len(remaining_files):
                skip_count = len(remaining_files)

            remaining_files = remaining_files[skip_count:]

            print(
                f"【跳过】子文件夹 {subfolder_name}: 跳过前 {skip_count} 张图片，剩余 {len(remaining_files)} 张图片"
            )
            csv_row.append(f"跳过{skip_count}张")

            subfolder_results.append(
                {
                    "task_idx": task_idx + 1,
                    "matched_file": None,
                    "status": f"SKIP_{skip_count}",
                    "time": 0,
                }
            )
            continue

        # 准备任务参数
        task_kwargs_copy = task_kwargs.copy()
        task_type = task_kwargs_copy.pop("task_type", None)  # 获取任务类型
        template_path = task_kwargs_copy.pop("template_path", None)

        # 根据任务类型确定检测函数
        detector_func = None
        if task_type == "cattail":
            detector_func = cattail
        elif task_type == "blover":
            detector_func = blover
        elif task_type == "cactus":
            detector_func = cactus
        # 可以在这里添加更多检测器函数的映射
        else:
            print(f"⚠️【警告】未知的任务类型 {task_type}，默认使用 cattail")
            detector_func = cattail

        # 执行任务并计时
        start_time = time.time()
        status, matched_file, _ = trails(
            image_files=remaining_files,
            folder_path=subfolder,
            template_path=template_path,
            detector_func=detector_func,  # 传递检测函数
            **task_kwargs_copy,
        )
        time_taken = time.time() - start_time
        total_time += time_taken

        # 记录结果
        subfolder_results.append(
            {
                "task_idx": task_idx + 1,
                "matched_file": matched_file,
                "status": status,
                "time": time_taken,
            }
        )

        print(
            f"【进展】子文件夹 {subfolder_name}: 任务 {task_idx + 1} ({task_type}), "
            f"匹配 {matched_file}, 状态 {status}, 耗时 {time_taken:.2f}秒"
        )

        # 更新CSV行
        csv_row.append(matched_file if status == "PASS" else status)

        # 处理任务失败或继续执行
        if status != "PASS":
            print(
                f"🟠【警告】子文件夹 {subfolder_name}: 任务 {task_idx + 1} 返回非PASS状态，跳过剩余任务"
            )
            csv_row.extend(["未执行"] * (len(tasks) - task_idx - 1))
            break

        # 更新剩余图片列表
        if matched_file in remaining_files:
            match_index = remaining_files.index(matched_file)
            remaining_files = remaining_files[match_index + 1:]
            print(
                f"【继续】子文件夹 {subfolder_name}: 继续已处理图片，剩余 {len(remaining_files)} 张图片"
            )

    # 异步写入CSV
    csv_queue.put(csv_row)
    print(f"【写入】子文件夹 {subfolder_name} 的结果已加入写入队列")
    
    return subfolder_name, subfolder_results, total_time


def csv_writer_worker(csv_filename, csv_queue):
    """
    CSV写入工作线程，负责异步写入数据
    
    参数:
        csv_filename: CSV文件路径
        csv_queue: 写入数据队列
    """
    max_retries = 3
    retry_delay = 0.1
    
    while True:
        try:
            # 从队列获取数据，如果队列为空则阻塞等待
            csv_row = csv_queue.get(timeout=1)
            
            # 检查是否为结束信号
            if csv_row is None:
                break
                
            # 重试写入
            for attempt in range(max_retries + 1):
                try:
                    with open(csv_filename, "a", newline="", encoding="utf-8-sig") as f:
                        csv.writer(f).writerow(csv_row)
                    print(f"【写入】数据已写入CSV: {csv_row[0]}")
                    break
                except PermissionError as e:
                    if attempt < max_retries:
                        print(f"【警告】写入CSV权限错误（重试 {attempt+1}/{max_retries}）")
                        time.sleep(retry_delay * (attempt + 1))
                    else:
                        print(f"🔴【致命错误】CSV写入失败，程序终止: {str(e)}")
                        os._exit(1)  # 直接终止程序
                except Exception as e:
                    print(f"🔴【致命错误】CSV写入异常，程序终止: {str(e)}")
                    os._exit(1)  # 直接终止程序
                    
            csv_queue.task_done()
            
        except queue.Empty:
            # 队列为空，继续等待
            continue
        except Exception as e:
            print(f"🔴【致命错误】写入线程异常，程序终止: {str(e)}")
            os._exit(1)  # 直接终止程序


def gate_multi_thread(parent_folder, tasks, task_headers, max_threads):
    """
    使用多线程处理母文件夹内所有子文件夹

    参数:
        parent_folder: 母文件夹路径
        tasks: 任务参数列表
        task_headers: CSV表头列表
        max_threads: 最大线程数

    返回:
        处理结果列表
    """
    start_total = time.time()

    # 准备CSV文件
    csv_header = ["子文件夹名"] + task_headers
    csv_filename = os.path.normpath(os.path.join(parent_folder, "处理结果.csv"))

    # 如果文件不存在，创建并写入表头
    if not os.path.exists(csv_filename):
        with open(csv_filename, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(csv_header)

    # 获取所有子文件夹
    subfolders = [f.path for f in os.scandir(parent_folder) if f.is_dir()]

    # 创建写入队列和启动写入线程
    csv_queue = queue.Queue()
    writer_thread = threading.Thread(target=csv_writer_worker, args=(csv_filename, csv_queue), daemon=True)
    writer_thread.start()

    # 使用线程池执行任务
    results = []
    print(f"🌾 Perf Garden 已就绪…… 请坐和放宽！")
    print(f"开始多线程处理，最大线程数: {max_threads}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        # 创建任务
        future_to_subfolder = {
            executor.submit(
                process_subfolder, subfolder, tasks, csv_filename, csv_queue
            ): subfolder
            for subfolder in subfolders
        }

        # 收集结果
        for future in concurrent.futures.as_completed(future_to_subfolder):
            subfolder = os.path.basename(future_to_subfolder[future])
            try:
                subfolder_name, subfolder_results, subfolder_time = future.result()
                results.append((subfolder_name, subfolder_results))
                print(
                    f"✅【完成】子文件夹 {subfolder_name} 处理完成，耗时: {subfolder_time:.2f}秒"
                )
            except Exception as e:
                print(f"⛔【错误】子文件夹 {subfolder} 处理出错: {e}")

    # 等待所有写入任务完成
    csv_queue.put(None)  # 发送结束信号
    writer_thread.join()  # 等待写入线程结束
    
    total_time = time.time() - start_total
    print(
        f"\n🌾 所有任务完成！总用时: {total_time:.2f}秒，Have A Nice Day~ 🌾🌾🌾🌾🌾🌾"
    )
    print(f"结果已保存到: {csv_filename}")

    return results


# 使用示例
if __name__ == "__main__":
    yaml_path = r"C:\test\q.yaml" # 替换为实际的YAML文件路径

    # 调用函数并获取结果
    results = gate_from_yaml(yaml_path)
