# cattail任务（模板匹配）

<cite>
**Referenced Files in This Document**   
- [PerfGarden.py](file://PerfGarden.py#L14-L85)
- [PerfGarden.py](file://PerfGarden.py#L267-L381)
- [README.md](file://README.md)
</cite>

## 目录
1. [简介](#简介)
2. [核心功能与算法](#核心功能与算法)
3. [参数详解](#参数详解)
4. [工作流程与控制逻辑](#工作流程与控制逻辑)
5. [实际应用场景](#实际应用场景)
6. [常见问题与解决方案](#常见问题与解决方案)
7. [性能优化建议](#性能优化建议)

## 简介

`cattail`任务是PerfGarden自动化框架中的核心图像识别功能之一，专为在图像序列中精确定位特定视觉元素而设计。该功能基于OpenCV的模板匹配算法（`matchTemplate`），通过在目标图像中滑动模板图像并计算相似度，实现对按钮、图标、标题等静态UI元素的高效检测。`cattail`特别适用于性能测试场景，如分析APP界面加载时间、用户交互响应延迟等，能够以毫秒级精度定位关键事件的发生时间点。

**Section sources**
- [PerfGarden.py](file://PerfGarden.py#L14-L85)
- [README.md](file://README.md)

## 核心功能与算法

`cattail`任务的核心是OpenCV的`cv2.matchTemplate`函数，采用`TM_CCOEFF_NORMED`（归一化相关系数匹配）算法。该算法将模板图像在目标图像上逐像素滑动，计算每个位置的相似度得分。得分范围为0到1，1表示完全匹配。为了提高鲁棒性，`cattail`在执行匹配前会将图像转换为灰度图，这使得匹配过程对颜色变化不敏感，但对图像的几何变形（如旋转、缩放）较为敏感。

```mermaid
flowchart TD
Start([开始 cattail 检测]) --> ValidateParams["参数校验\nthreshold: 0-1\ncrop: -99~99"]
ValidateParams --> ReadImages["安全读取图片\nimg_path 和 template_path"]
ReadImages --> CheckRead["图片读取成功？"]
CheckRead --> |否| ReturnError["返回 EC02 错误"]
CheckRead --> |是| CropImage["执行裁剪操作\ncrop != 0 ?"]
CropImage --> |是| ApplyCrop["根据 crop 值裁剪\n>0: 保留底部\n<0: 保留顶部"]
CropImage --> |否| SkipCrop["跳过裁剪"]
ApplyCrop --> SkipCrop
SkipCrop --> ValidateSize["模板尺寸校验\ntemplate <= image ?"]
ValidateSize --> |否| ReturnSizeError["返回 EC03 错误"]
ValidateSize --> |是| ConvertGray["转换为灰度图\nBGR -> GRAY"]
ConvertGray --> ExecuteMatch["执行模板匹配\nmatchTemplate()"]
ExecuteMatch --> FindMax["寻找最大匹配值\nminMaxLoc()"]
FindMax --> ProcessConfidence["处理置信度\nround(max_val, 2)"]
ProcessConfidence --> CompareThreshold["置信度 >= threshold ?"]
CompareThreshold --> |是| Matched["matched = True"]
CompareThreshold --> |否| NotMatched["matched = False"]
Matched --> ReturnPass["返回 PASS 状态"]
NotMatched --> ReturnPass
ReturnPass --> End([返回结果元组\n(status, matched, confidence, duration)])
ReturnError --> End
ReturnSizeError --> End
```

**Diagram sources**
- [PerfGarden.py](file://PerfGarden.py#L14-L85)

**Section sources**
- [PerfGarden.py](file://PerfGarden.py#L14-L85)

## 参数详解

`cattail`任务通过一系列参数提供高度的灵活性和精确的控制，使其能够适应各种复杂的检测场景。

### template（模板图片路径）
- **描述**：指定用于匹配的模板图像文件路径。这是`cattail`任务的必需参数。
- **要求**：必须是一个有效的图像文件（如.jpg, .png）。最佳实践是从目标设备的截图中直接“裁剪”出需要识别的元素，而非使用“截图”或从不同分辨率的设备获取的图片，以确保像素级匹配的准确性。
- **Section sources**
  - [PerfGarden.py](file://PerfGarden.py#L14-L85)
  - [README.md](file://README.md)

### threshold（匹配相似度阈值）
- **描述**：定义匹配成功的最低相似度阈值，范围在0到1之间。
- **影响**：值越高，匹配要求越严格。例如，阈值0.9表示只有当相似度达到90%以上时才判定为匹配成功。默认值为0.9，对于精确匹配通常建议设置为0.9以上。在光照变化或轻微模糊的场景下，可适当降低阈值（如0.7-0.8）以提高鲁棒性。
- **Section sources**
  - [PerfGarden.py](file://PerfGarden.py#L14-L85)
  - [README.md](file://README.md)

### crop（可选裁剪区域）
- **描述**：一个整数，表示对目标图像进行裁剪的比例，范围为-99到99。
- **格式与行为**：
  - **正值**（如 `crop: 50`）：从图像底部向上裁剪，保留底部50%的区域。适用于检测屏幕底部的按钮。
  - **负值**（如 `crop: -30`）：从图像顶部向下裁剪，保留顶部30%的区域。适用于检测屏幕顶部的标题栏。
  - **零值**（`crop: 0`）：不进行裁剪，使用完整图像。
- **优势**：通过限定搜索区域，可以显著提升匹配速度和准确性，同时减少因界面其他部分变化（如动态内容）导致的误匹配。
- **Section sources**
  - [PerfGarden.py](file://PerfGarden.py#L14-L85)
  - [README.md](file://README.md)

### fade（是否启用渐进式处理模式）
- **描述**：一个布尔值，控制匹配的触发逻辑。
- **行为**：
  - **`fade: false`**（默认）：一旦检测到匹配，立即返回结果。适用于检测“进入页面”或“元素出现”的场景。
  - **`fade: true`**：必须先检测到匹配，然后继续检测直到匹配消失，才返回匹配消失时的图片。适用于检测“离开页面”或“加载完成”（元素消失）的场景。
- **Section sources**
  - [PerfGarden.py](file://PerfGarden.py#L267-L381)
  - [README.md](file://README.md)

### leap（跳跃步长）
- **描述**：一个正整数，表示在图像序列中跳跃检查的步长。
- **工作原理**：默认值为3，表示每隔2张图片检查一次（即检查第3、6、9...张）。当在跳跃模式下检测到匹配时，系统会自动回退到匹配点之前的`leap-1`张图片，然后以`leap=1`的步长进行逐帧检查，确保不会漏检。
- **优势**：极大地提高了处理速度，尤其在处理长序列时，能实现“智能间隔”检测，兼顾效率与准确性。
- **Section sources**
  - [PerfGarden.py](file://PerfGarden.py#L267-L381)
  - [README.md](file://README.md)

## 工作流程与控制逻辑

`cattail`任务的执行由`trails`函数协调，形成一个高效的流水线。`trails`函数负责管理图像序列的遍历、参数传递和状态控制。

```mermaid
sequenceDiagram
participant User as "用户配置"
participant Trails as "trails函数"
participant Cattail as "cattail函数"
participant Image as "图像序列"
User->>Trails : 提供 image_files, folder_path, 参数
Trails->>Trails : 初始化参数 (leap, fade, crop)
loop 遍历图像序列
Trails->>Trails : 计算当前索引 i
Trails->>Image : 获取 img_path
Trails->>Cattail : 调用 cattail(img_path, template_path, threshold, crop)
Cattail->>Cattail : 执行匹配并返回 (status, matched, confidence, duration)
Trails->>Trails : 检查 status 是否为 "PASS"
alt status != "PASS"
Trails->>User : 返回 "ERROR"
break
end
Trails->>Trails : 检查是否在跳跃模式 (leap > 1)
alt 在跳跃模式且 matched
Trails->>Trails : 回退 i = i - (leap - 1)
Trails->>Trails : 设置 leap = 1 (进入逐帧模式)
else
Trails->>Trails : 检查是否在逐帧模式 (leap == 1)
alt 在逐帧模式
alt fade == false 且 matched
Trails->>User : 返回匹配文件名 (出现)
break
else if fade == true
alt matched
Trails->>Trails : 设置 waiting_for_fade = true
else if waiting_for_fade 且 not matched
Trails->>User : 返回匹配文件名 (消失)
break
end
end
end
end
Trails->>Trails : i += leap
end
Trails->>User : 若未找到，返回 "UNFOUND"
```

**Diagram sources**
- [PerfGarden.py](file://PerfGarden.py#L267-L381)

**Section sources**
- [PerfGarden.py](file://PerfGarden.py#L267-L381)

## 实际应用场景

`cattail`任务在性能测试中有着广泛的应用。一个典型的场景是分析“AI对话应用中上传图片”的性能指标。

1.  **检测导入开始**：配置`cattail`任务，使用“导入按钮”的模板图片，设置`crop: 30`（保留底部30%），并设置`fade: true`。当系统检测到“导入按钮”从界面上消失时，即判定为图片上传开始，记录该时间点。
2.  **检测上传完成**：后续可结合`blover`任务检测上传中的“加载圆圈”，并同样使用`fade: true`来检测圆圈消失，从而确定上传完成的时间点。
3.  **检测AI回复完成**：最后，再次使用`cattail`任务，匹配“分享”或“完成”等固定图标，通过`fade: false`检测其出现，即可确定AI回复完成的时间。

通过串联多个`cattail`任务，可以精确地量化整个交互流程的各个阶段耗时。

**Section sources**
- [README.md](file://README.md)

## 常见问题与解决方案

### 匹配失败（EC02）
- **原因**：最常见的原因是模板图片与目标图片的像素尺寸不匹配。例如，使用了不同分辨率设备的截图作为模板。
- **解决方案**：务必从目标设备的截图中直接“裁剪”出模板图片，确保其尺寸和内容与待检测图像完全一致。

### 匹配失败（光照变化）
- **原因**：环境光照变化导致图像亮度、对比度发生改变，影响灰度匹配的准确性。
- **解决方案**：
  1.  **调整阈值**：适当降低`threshold`值（如从0.9降至0.8），以容忍更大的相似度差异。
  2.  **优化模板**：选择在多种光照条件下都较为稳定的界面元素作为模板，或使用经过预处理（如标准化亮度）的模板图像。

**Section sources**
- [README.md](file://README.md)

## 性能优化建议

为了最大化`cattail`任务的处理效率，建议采取以下措施：
- **合理使用`crop`参数**：始终将搜索范围限定在目标元素可能出现的区域，避免全图搜索。
- **设置合适的`leap`值**：对于长序列，使用较大的`leap`值（如5或10）可以显著缩短处理时间。
- **压缩图片尺寸**：在不影响识别精度的前提下，将图片宽度缩小至720像素左右，可以大幅提升OpenCV的处理速度。
- **利用多线程**：通过YAML配置文件中的`max_threads`参数，充分利用多核CPU并行处理多个任务文件夹。