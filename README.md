# 🌾 Perf Garden - 性能花园，自然快乐

Perf Garden 是一个基于 Python 与 OpenCV 的高效图像自动化框架，专为批量图像识别设计。它能胜任"录屏分帧打标"测试 APP 性能等场景中的人工机械操作问题。不仅速度超快，还能适应多种使用场景，同时支持流水线和多线程处理，让大量图像任务变得轻松自如。

## 值得一试

- 快速 🚀：采用经优化的 OpenCV 算法，能在 1 秒内识别上百张图片；配合多线程、智能间隔、跳过识别和裁剪等加速策略，远快于传统人工或 OCR 识别方式。
- 智能 ♻️：无论你想打标多少次，识别顶部标题还是底部按钮，判断页面进入还是离开，甚至识别无文字的图标或加载动画，都能轻松设置不同场景的处理流水线。
- 稳健 🦾：自动处理各种异常情况，单个任务出错不会影响整体流程，同时实时将结果写入 CSV 报告，确保工作进度不会丢失。

## 快速开始

1. 安装必要环境：`pip install opencv-python numpy pyyaml`
2. 准备图片，将每组任务图片按数字命名，分别放入文件夹，再将所有文件夹放入一个总文件夹。
3. 配置 YAML 文件，将其路径写入代码，然后运行本代码。
4. 坐和放宽！在终端查看实时进展，所有结果会自动保存到总文件夹中的 CSV 文件里。

提示：如果你的文件还是视频，不妨试试项目附带的脚本，可通过 FFmpeg 批量分帧并压缩图片，且文件结构符合本项目需求。

### 文件结构

``` text
总文件夹/
├── config.yml          # 配置文件
├── task_1/             # 任务 1 图片组
│   ├── 1.jpg           # 按数字顺序命名的图片
│   ├── 2.jpg          
│   └── ...
├── task_2/             # 任务 2 图片组
│   └── ...
└── 处理结果。csv         # 自动生成的报告

templates/              # 存放模板图片
```

## 配置文件

会自上而下依次执行所有任务，完成后将用剩余图片执行后续任务。如果图片用完或任务出错，自动跳过所有剩余任务。

```YAML
- path: "……/samples" #总文件夹路径，注意引号和斜杆
- max_threads: 8 #最大多线程数

- cattail: # 任务 1，使用 cattail 检测方法（模板匹配）
    - template: "……/templates/button.jpg" # 必填，cattail 检测方法的模板路径

- skip: 10 # 任务 2，跳过 10 张图片继续

- cattail: # 任务 3，使用 cattail 检测方法（模板匹配）
    - template: "……/templates/next_button.jpg" # 必填，cattail 检测方法的模板路径
    - threshold: 0.8 # cattail 检测可信度阈值
    - crop: 50 # 从下向上保留图片底部 50%
    - fade: false # 检测目标出现
    - leap: 2 # 每两张图检查一次

- blover: # 任务 4，使用 blover 检测方法（检测圆圈）
    - threshold: 1 # blover 应检测几个圆圈
    - crop: 50 # 从下向上保留图片底部 50%
    - fade: true # 检测目标出现后消失
    - leap: 2 # 每两张图检查一次
```

## 检测方法

### cattail 模板匹配

此方法在任务图片中查找模板内容，就是"在大图中找小图"。它基于 OpenCV 优化的滑动窗口技术，能在毫秒级完成识别。

cattail 适合大多数常见任务，如识别按钮、图标或标题等固定元素。使用时，你需要先准备要识别的模板，比如从任务图片中**裁剪**出按钮图片，然后将模板路径写入 YAML 文件。

注意：模板匹配对图像大小和角度很敏感，所以应该"裁剪"任务图片而非"截图"，不同尺寸的设备需要不同的模板。由于系统使用灰度图处理，所以对颜色变化不敏感。如果模板位于复杂背景中，可能难以识别。另外，模板图片不能比任务图片大。

- threshold：取值 0~1，默认 0.8。表示模板匹配的可信度，值越高要求越严格，准确匹配通常在 0.9 以上。

报错代码：EC01，参数错误；EC02，读取图片失败；EC03，模板图片比任务图片大。

### blover 检测圆圈

此方法能检测图片中的圆圈数量，基于 OpenCV 的霍夫变换数学原理，可在复杂背景中快速识别圆形，无需逐像素分析。

blover 特别适合"图片上传"场景，当页面只有加载中的圆圈且背景复杂，无法用模板匹配时，它能识别上传过程中的"圆圈动画"。使用时，建议先用 cattail 定位到上传前的图片，再用 blover 确认上传状态，可设置`fade=true`检测圆圈出现后消失，从而确认图片上传完成。

注意：如需更复杂的识别调整，请查看代码中的`param2`参数。

- threshold：正整数，默认 1，表示图中应有几个圆圈。一般单张图片上传只有一个圆圈。

报错代码：EB01，参数错误；EB02，读取图片失败。

### skip 跳过图片

此方法可跳过一定数量的图片，适用于处理开始时的无用时间段，或跳过加载时间长、过渡动画干扰等场景。合理使用可有效缩短任务处理时间，同时提高准确度。

注意：skip 不可配置通用参数。

- skip: 正整数，表示要跳过的图片数量。

## 通用参数

### 全局参数

- path：总文件夹路径，决定任务的处理范围和 CSV 结果的输出位置。请注意使用正确的斜杠格式（/而非、）并加上引号，避免路径解析错误。
- max_threads：正整数，用于设置最大并行线程数。会根据此值并行处理每个文件夹内的任务，根据处理器性能合理配置，可大幅提升处理速度，但会占用更多资源。

### 配置参数

以下配置参数可用于大多数检测方法，合理配置不仅能加速处理过程，还能提升识别准确度。

- crop：取值 -99~99，默认为 0。
  - 正值：从下向上裁剪图片，保留底部指定百分比，适合识别底部按钮等元素。
  - 负值：从上向下裁剪图片，保留顶部指定百分比，适合识别顶部标题等元素。
  - 设为 0：不进行裁剪，使用完整图片。

- fade：布尔值，默认为 false。
  - false：目标一旦检测到出现就记录，适合识别"进入页面"等场景。
  - true：只有当目标先出现后再消失时才记录，适合识别"离开页面"等场景。

- leap：正整数，默认为 3。
  - 表示每隔几张图片检测一次，发现目标后会自动回溯检查附近和后续图片。
  - 合理设置“智能间隔”，可大幅提升处理速度且不会漏检。
  - 设为 1 则逐一检测每张图片，相当于不启用智能间隔。

## 上手实践

下面通过一个常见场景来演示 Perf Garden 的实际应用：分析"AI 对话上传图片"的性能指标。这个测试包含三个关键时间点：

1. 导入图片开始计时
2. 图片上传完成
3. AI 完成回复

### 准备工作

首先，将录屏分帧后的图片按测试轮次放入不同文件夹，再将所有文件夹集中到一个总文件夹。在新建的 YAML 配置文件中，将总文件夹路径填入 path 字段。

### 配置任务

任务一：检测导入开始

- 选择通用的 cattail 方法，因为导入按钮是固定元素，
- 裁剪底部 30%区域 (crop: 30)，因为导入按钮位于屏幕底部，
- 设置 fade 为 true，表示我们要检测按钮消失的时刻（离开页面开始计时）。

任务二：检测上传完成

- 选择专门的 blover 方法，适合分析上传状态，
- 裁剪顶部 50%区域 (crop: -50)，因为上传图片显示在屏幕上方，
- 设置 fade 为 true，表示我们需要检测上传状态消失的时刻（上传完成）。

任务三：检测 AI 回复完成

- 再次使用 cattail 方法检测固定元素，
- 裁剪底部 50%区域 (crop: 50)，因为分享图标位于屏幕下方，
- 使用默认 fade 值 (false)，因为只需检测分享图标出现即可。

### 配置示例

```YAML
- path: "C:/Users……/测试"

- cattail:
    - template: "c:/Users……/button.jpg"
    - crop: 30
    - fade: true

- blover:
    - crop: -50
    - fade: true

- skip: 80

- cattail:
    - template: "c:/Users……/share.jpg"
    - crop: 50
```

### 运行结果

在代码底部填入 YAML 配置文件地址并运行：

```Python
if __name__ == "__main__":
    yaml_path = r"C:\Users……测试、config.yml"

    results = gate_from_yaml(yaml_path)
```

终端输出显示整个处理过程仅用 0.67 秒就完成了 400 多张图片的分析：

```text
🌾 Perf Garden 已就绪…… 请坐和放宽！
开始多线程处理，最大线程数：8
【进展】子文件夹 任务 (2): 任务 1 (cattail), 匹配 frame_00032.jpg, 状态 PASS, 耗时 0.41 秒
【继续】子文件夹 任务 (2): 继续已处理图片，剩余 116 张图片
【进展】子文件夹 任务 (2): 任务 2 (blover), 匹配 frame_00042.jpg, 状态 PASS, 耗时 0.12 秒
【继续】子文件夹 任务 (2): 继续已处理图片，剩余 106 张图片
【跳过】子文件夹 任务 (2): 跳过前 80 张图片，剩余 26 张图片
【进展】子文件夹 任务 (2): 任务 4 (cattail), 匹配 frame_00137.jpg, 状态 PASS, 耗时 0.12 秒
【继续】子文件夹 任务 (2): 继续已处理图片，剩余 11 张图片
【写入】子文件夹 任务 (2) 的结果已写入 CSV

 ……

✅【完成】子文件夹 任务 (2) 处理完成，耗时：0.65 秒
✅【完成】子文件夹 任务 (1) 处理完成，耗时：0.66 秒
✅【完成】子文件夹 任务 (3) 处理完成，耗时：0.66 秒

🌾 所有任务完成！总用时：0.67 秒，Have A Nice Day~ 🌾🌾🌾🌾🌾🌾
结果已保存到：C:\Users……\测试、处理结果。csv
```

打开生成的 CSV 文件，可以查看每个测试轮次的关键时间点：

|子文件夹名 |cattail1       |blover1        |skip1|cattail2       |
|------|---------------|---------------|-----|---------------|
|任务 (2)|frame_00032.jpg|frame_00042.jpg|跳过 80 张|frame_00137.jpg|
|任务 (1)|frame_00032.jpg|frame_00042.jpg|跳过 80 张|frame_00137.jpg|
|任务 (3)|frame_00032.jpg|frame_00042.jpg|跳过 80 张|frame_00137.jpg|

从结果可以清晰看出每个关键节点对应的帧，通过帧号计算即可得出精确的性能指标。

## 常见问题

- Perf Garden 的性能如何？
  - 根据实际测试，对于包含 200 多帧图片的 5 轮测试，使用 cattail 方法在多线程下只需 1.74 秒即可完成识别，而传统 OCR 识别方法则需要 84.6 秒。两种方法的识别准确度基本相当，但 Perf Garden 的处理速度约快 50 倍…… 而你现在可以更好的工作 ;-)
- cattail 为何一直匹配失败？
  - 最常见的原因是模板图片来源不当。请确保模板图片是直接从任务图片中裁剪得到的，而非通过截图或从不同尺寸设备获取的图像。像素大小的变化会显著影响模板匹配的准确度。
- 如何进一步提升处理速度？
  - 减小图片尺寸是最有效的方法之一。对于手机截屏，建议将宽度缩小至 720 像素即可，这能在保持识别质量的同时大幅提升处理性能。
  - 如果你还未从视频中提取图片帧，可以使用本项目附带的分帧脚本，它不仅能自动提取帧，还能同时压缩图片尺寸，一步到位提高整体效率。

## 更新计划

后续将为花园增加增加更多的高效检测方法，适配更多的场景。“用图像的方法解决图像的问题”，让花园开满鲜花，让工作人员自然快乐。🌾

## 贡献许可

本项目基于 OpenCV 开发，遵循 Apache 2.0 许可协议，特此对 OpenCV 项目表示诚挚感谢。项目由 逊狼 开发，并得到了 Claude-3.7-Sonnet 和 Deepseek-R1 的 AI 协助，在此一并致谢。
