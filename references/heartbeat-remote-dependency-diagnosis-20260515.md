# 心跳远程依赖诊断模式

## 触发场景
心跳脚本执行步骤失败，错误信息包含：
- `Connection closed by <IP> port 22`（SSH 连接中途断开）
- `未找到XXX报告`（远程文件/目录不存在）

## 诊断流程

```
心跳失败
    ↓
1. 检查 status.json 中的错误信息
    ↓
2. SSH 到远程服务器验证路径
   - 目录是否存在？
   - 文件是否存在？
   - 权限是否正确？
    ↓
3. 检查心跳日志历史
   - 之前是否成功执行过？
   - 成功结果是否已满足需求？
    ↓
4. 确定根因
   - 远程依赖缺失 → 需要部署/恢复
   - SSH 不稳定 → 重试或优化传输方式
   - 已完成 → 无需再次执行
```

## 常见根因

| 错误 | 根因 | 解决方案 |
|------|------|----------|
| `Connection closed by port 22` | SSH 连接中途断开 | 检查远程目录是否存在，大文件传输可能超时 |
| `未找到XXX报告` | 远程目录/文件不存在 | 部署缺失的工具/恢复目录 |
| `No such file or directory` | 远程路径配置错误 | 修正心跳配置中的路径 |

## 实例：AWVS 下载失败

**现象**：
```
❌ 步骤7失败: 下载失败: Connection closed by 36.151.146.180 port 22
```

**诊断**：
```bash
# 1. 检查远程目录
ssh root@server "ls -la /home/tool/Awvs-Report-Tool/"
# 结果: No such file or directory

# 2. 检查心跳日志
tail -50 heartbeat.log
# 发现: 00:14:11 已成功下载报告到本地

# 3. 结论: 目录缺失，但任务已由之前执行完成
```

**结论**：远程目录 `/home/tool/Awvs-Report-Tool/` 不存在，但报告已在 00:14:11 成功下载，无需再次执行。

## 验证命令

```bash
# 检查远程目录
ssh root@<server> "ls -la <path>"

# 检查远程文件
ssh root@<server> "find <base_path> -name '<pattern>' -mmin -60"

# 检查本地已下载结果
ls -la /x/rank/hwxinxisouji/liuliang/results/<date>/
```

## 关键原则

1. **先验证再报错**：SSH 连接断开可能是路径不存在导致的
2. **检查历史执行**：心跳可能已成功执行过，当前只是重复尝试
3. **远程依赖清单**：心跳脚本依赖的远程路径应文档化
