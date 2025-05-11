import concurrent.futures
import csv
import os
import re
import threading
import time

import cv2  # pip install opencv-python
import numpy as np  # pip install numpy
import yaml  # pip install pyyaml


## 香蒲：图片模板匹配
def cattail(
    img_path: str, template_path: str, threshold: float = 0.8, crop: int = 0
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
            img = img[h - new_h : h, :]
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
        gray = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
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
            gray = gray[h - new_h : h, :]
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
        dp=1,  # 保持默认分辨率
        minDist=100,  # 增大圆心最小距离
        param1=100,  # Canny边缘检测参数
        param2=70,  # 增大累加器阈值(关键参数，越大检测越严格)
        minRadius=10,  # 设置最小半径，避免小型圆形文字
        maxRadius=50,  # 根据实际需要调整最大半径
    )

    # 计算结果
    confidence = 0
    if circlEB is not None:
        confidence = len(circlEB[0])

    # 判断是否匹配
    matched = confidence == threshold

    duration = time.time() - start_time

    return ("PASS", matched, confidence, duration)


## 核心逻辑调度
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

    i = leap - 1  # 起始索引（对应第leap张图片）
    waiting_for_fade = False  # 是否在等待匹配消失
    first_match = None  # 第一个匹配的图片
    result_found = False  # 是否找到结果

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
        # print(f"{img_file}: {result}")

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
            task_type_counts[task_type] = task_type_counts.get(task_type, 0) + 1
            task_headers.append(f"{task_type}{task_type_counts[task_type]}")

            # 提取任务参数
            task_kwargs = {"task_type": task_type}
            if task_type == "skip":
                # 对于skip指令，直接存储要跳过的图片数
                task_kwargs["skip_count"] = task_config
            else:
                for param in task_config:
                    for key, value in param.items():
                        if key == "template":
                            task_kwargs["template_path"] = os.path.normpath(value)
                        else:
                            task_kwargs[key] = value

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


def process_subfolder(subfolder, tasks, csv_filename, csv_lock):
    """
    处理单个子文件夹的所有任务，在单独线程中执行

    参数:
        subfolder: 子文件夹路径
        tasks: 任务参数列表
        csv_filename: CSV结果文件路径
        csv_lock: 用于CSV写入的线程锁

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
            remaining_files = remaining_files[match_index + 1 :]
            print(
                f"【继续】子文件夹 {subfolder_name}: 继续已处理图片，剩余 {len(remaining_files)} 张图片"
            )

    # 线程安全地写入CSV
    with csv_lock:
        with open(csv_filename, "a", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(csv_row)
        print(f"【写入】子文件夹 {subfolder_name} 的结果已写入CSV")

    return subfolder_name, subfolder_results, total_time


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

    # 创建线程锁用于CSV写入
    csv_lock = threading.Lock()

    # 使用线程池执行任务
    results = []
    print(f"🌾 Perf Garden 已就绪…… 请坐和放宽！")
    print(f"开始多线程处理，最大线程数: {max_threads}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        # 创建任务
        future_to_subfolder = {
            executor.submit(
                process_subfolder, subfolder, tasks, csv_filename, csv_lock
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

    total_time = time.time() - start_total
    print(
        f"\n🌾 所有任务完成！总用时: {total_time:.2f}秒，Have A Nice Day~ 🌾🌾🌾🌾🌾🌾"
    )
    print(f"结果已保存到: {csv_filename}")

    return results


# 使用示例
if __name__ == "__main__":
    yaml_path = r"C:\Users……\测试\config.yml"  # 替换为实际的YAML文件路径

    # 调用函数并获取结果
    results = gate_from_yaml(yaml_path)
