# 后续工作流陷阱与注意事项

本文档记录工作流执行后的后续处理（如 JS 敏感信息分析、AWVS 报告分析）中遇到的陷阱和注意事项。

---

## 1. wih_monitor.py 不触发 JS 分析工作流

### 问题描述

**症状**: WIH 完成检测 cronjob 运行正常，但 JS 敏感信息分析工作流未执行

**原因**: `wih_monitor.py` 脚本只更新 status.json，未实际调用 workflow-manager 执行工作流（代码中有 TODO 注释）

### 代码现状

```python
# wih_monitor.py 第 76-77 行
# TODO: 这里需要调用workflow-manager执行JS敏感信息分析工作流
# 由于技能无法直接调用，这里先记录信号
```

### 临时解决方案

主 AI 检测到 `heartbeat.wih.complete == true` 且 `analyzed == false` 时，手动执行 JS敏感信息分析工作流

### 长期方案

修复 wih_monitor.py，通过 Hermes cronjob 或 delegate_task 触发工作流

---

## 2. JS 敏感信息分析误报

### 问题描述

**症状**: Critical 级别发现 AWS Access Key、Google API Key，但上下文显示二进制数据

**原因**: 视频/音频播放器 JS 文件（如 jessibuca.js）包含 base64 编码的二进制数据，正则匹配误判为 API Key

### 识别特征

| 特征 | 说明 |
|------|------|
| 匹配值模式 | 包含大量 `AAAA`、`AIZA`、`AKIA` 等连续字符 |
| 上下文特征 | 显示 `XX...XXX` 或 `KwAAAA...` 等二进制特征 |
| 文件名关键词 | `jessibuca`、`player`、`video`、`audio`、`codec` |

### 处理方式

1. 检查匹配值的上下文是否为二进制数据
2. 排除视频/音频播放器相关 JS 文件
3. 对 Critical 级别发现进行人工复核

### 示例误报

```
来源: https://111.198.60.180:1443/jessibuca.js
匹配: AIZACOAAAAAB0GaVAX4GSAhAEmQAhkAI4AhAEmQ
上下文: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX... (二进制数据)
判断: 误报 - jessibuca 是视频播放器，该数据为视频解码器数据
```

### 根本原因

JS 敏感信息分析工具使用的正则表达式（如 `AKIA[0-9A-Z]{16}`）无法区分：
- 真实的 AWS Access Key
- Base64 编码的二进制数据（视频/音频 codec 数据）

### 改进建议

1. **排除已知播放器文件**: 在扫描前排除 `jessibuca`、`hls.js`、`video.js` 等播放器文件
2. **上下文验证**: 检查匹配值周围是否有大量连续相同字符（`AAAA...`）
3. **熵值检测**: 真实密钥熵值高，二进制数据熵值相对较低

---

## 3. AWVS 报告合并 Bug

### 问题描述

**症状**: AWVS 报告文件名显示 `2scans`，但实际只包含 2 个扫描结果，而非全部扫描

**原因**: AWVS Report Tool 的 `report` 命令有合并限制或 Bug

### 影响

- 分析结果不完整
- 需要多次运行报告生成

### 解决方案

1. 检查 `python3 awvs14_script.py status` 确认总扫描数
2. 对比报告中的扫描数与 API 返回的扫描数
3. 如不一致，手动合并多个报告

---

## 版本历史

- v1.0.0 (2026-05-11): 初始版本 - wih_monitor.py TODO 陷阱、JS 分析误报、AWVS 报告合并 Bug
