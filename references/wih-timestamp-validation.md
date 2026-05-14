# WIH 压缩包时间戳验证问题

## 问题描述

在 `heartbeat.py` 的 WIH 完成检测逻辑中，使用压缩包时间戳与工作流启动时间比较来判断是否完成：

```python
if started_at > 0 and file_timestamp > started_at:
    is_complete = True
else:
    log(f"⚠️ WIH进程不存在，但压缩包是历史文件")
```

## 问题场景

1. WIH 进程在工作流启动前就已运行并生成压缩包
2. 工作流启动时 `workflow_started_at` 记录当前时间
3. WIH 压缩包时间戳 < 工作流启动时间
4. 系统误判为"历史文件"，无法识别为有效结果

## 示例

```
工作流启动时间: 17:30:02 (1778491802)
WIH 压缩包时间: 17:29:33 (1778491773)
判断结果: file_timestamp < started_at → "历史文件"
```

## 解决方案

### 方案 A：内容验证（推荐）

检查压缩包内容而非仅依赖时间戳：

```python
def validate_wih_content(tar_path: str, expected_urls: list) -> bool:
    """验证压缩包内容是否匹配本次工作流"""
    with tarfile.open(tar_path, 'r:gz') as tar:
        # 1. 检查 url.txt 是否包含预期 URL
        url_file = tar.extractfile(f"{tar_name}/url.txt")
        if url_file:
            actual_urls = set(url_file.read().decode().strip().split('\n'))
            if actual_urls == set(expected_urls):
                return True
    
    # 2. 检查 CSV 文件数量
    # 3. 检查截图数量（如果有）
    return False
```

### 方案 B：宽松时间窗口

允许一定的时间差：

```python
# 允许压缩包时间早于启动时间最多 30 分钟
TIME_TOLERANCE = 1800  # 秒

if file_timestamp > (started_at - TIME_TOLERANCE):
    is_complete = True
```

### 方案 C：进程状态优先

如果 WIH 进程已停止且压缩包存在，直接接受结果：

```python
if process_count == 0 and tar_file_exists:
    # 进程已停止，检查压缩包有效性
    if validate_tar_structure(tar_path):
        is_complete = True
```

## 最佳实践

1. **时间戳 + 内容双重验证**：不仅比较时间，还要验证内容
2. **记录工作流输入**：保存 `url.txt` 的哈希值或内容，用于后续验证
3. **人工确认机制**：当自动判断不确定时，更新状态并等待人工确认

## 相关文件

- `~/.hermes/workflows/home漏扫/heartbeat.py` - WIH 完成检测逻辑
- `~/.hermes/workflows/home漏扫/status.json` - 工作流状态
- `/x/rank/hwxinxisouji/liuliang/results/{date}/wih/` - WIH 结果目录
