# skip跳过图片

<cite>
**本文档引用的文件**  
- [README.md](file://README.md)
- [PerfGarden.py](file://PerfGarden.py)
</cite>

## 目录
1. [简介](#简介)
2. [skip功能的作用](#skip功能的作用)
3. [实现方式](#实现方式)
4. [YAML配置示例](#yaml配置示例)
5. [与后续检测任务的协同工作](#与后续检测任务的协同工作)
6. [优势与注意事项](#优势与注意事项)
7. [实际应用案例](#实际应用案例)

## 简介
skip功能是Perf Garden框架中用于控制时间序列图像处理流程的重要机制。它并非图像分析算法，而是一种流程控制逻辑，旨在通过跳过指定数量的初始图片帧，排除视频录制初期的无效或过渡画面（如APP启动黑屏、加载界面等），从而提高整体处理效率和准确性。

## skip功能的作用
skip功能主要用于处理视频录制初期的无效时间段，例如APP启动时的黑屏、加载动画或其他过渡画面。这些画面通常不包含任何有意义的信息，但会占用大量的处理时间和计算资源。通过配置skip指令，用户可以指定跳过一定数量的图片帧，从而直接从有效画面开始进行后续的检测任务。

## 实现方式
skip功能的实现主要依赖于`process_subfolder`函数中的逻辑处理。当解析到`skip`任务时，系统会根据配置的`skip_count`值，从当前剩余的图片列表中移除相应数量的图片帧。具体实现如下：

1. **任务识别**：在`process_subfolder`函数中，系统会检查当前任务的`task_type`是否为`skip`。
2. **跳过处理**：如果任务类型为`skip`，则从`remaining_files`列表中移除前`skip_count`张图片。
3. **更新状态**：更新剩余图片列表，并记录跳过操作的日志信息。

```python
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
```

**Section sources**
- [PerfGarden.py](file://PerfGarden.py#L362-L518)

## YAML配置示例
在YAML配置文件中，skip功能通过`skip`关键字和`count`参数来定义。以下是一个典型的配置示例：

```yaml
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

在这个示例中，`skip: 80`表示跳过前80张图片，然后继续执行后续的检测任务。

**Section sources**
- [README.md](file://README.md#L150-L160)

## 与后续检测任务的协同工作
skip功能与后续的检测任务（如`cattail`和`blover`）协同工作，构成完整的处理流水线。具体流程如下：

1. **初始化**：系统读取YAML配置文件，解析出所有任务。
2. **执行skip**：首先执行`skip`任务，跳过指定数量的图片帧。
3. **执行检测任务**：从跳过后的图片帧开始，依次执行`cattail`和`blover`等检测任务。
4. **结果记录**：将每个任务的匹配结果记录到CSV文件中。

这种流水线式的处理方式确保了只有有效的图片帧被用于检测，从而提高了整体处理效率。

**Section sources**
- [PerfGarden.py](file://PerfGarden.py#L362-L518)
- [README.md](file://README.md#L150-L160)

## 优势与注意事项
### 优势
- **简化流程控制**：通过简单的配置即可实现复杂的流程控制，避免了手动处理无效画面的繁琐操作。
- **避免无效计算**：跳过无效画面可以显著减少不必要的计算，提高处理速度。
- **提高准确性**：排除干扰画面，确保检测任务只在有效画面中进行，提高了检测的准确性。

### 注意事项
- **准确预估跳过帧数**：用户需要准确预估跳过帧数，以防止遗漏关键画面。过多的跳过可能导致重要信息丢失，过少的跳过则无法有效排除无效画面。
- **配置合理性**：确保skip任务的配置合理，避免与其他任务冲突或导致流程中断。

**Section sources**
- [README.md](file://README.md#L150-L160)

## 实际应用案例
### 跳过前5秒启动时间后再进行按钮识别
假设我们需要分析一个APP的启动过程，其中前5秒为启动黑屏，之后才是有效的操作界面。我们可以通过以下配置实现：

```yaml
- path: "C:/Users……/测试"

- skip: 50  # 假设每秒10帧，跳过前5秒

- cattail:
    - template: "c:/Users……/button.jpg"
    - crop: 30
    - fade: true
```

在这个配置中，`skip: 50`表示跳过前50张图片（即前5秒），然后从第51张图片开始执行`cattail`检测任务，识别按钮。这样可以确保检测任务只在有效画面中进行，避免了启动黑屏对检测结果的影响。

**Section sources**
- [README.md](file://README.md#L150-L160)
- [PerfGarden.py](file://PerfGarden.py#L362-L518)