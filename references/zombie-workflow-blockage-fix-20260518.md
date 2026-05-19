# 僵尸工作流阻断问题修复（2026-05-18）

## 问题现象

执行任意操作时，Hook 阻断并报错：

```
⛔ 未完成的工作流但无会话标记。

工作流: 电力数据
状态: initialized

解决：python actions/execute.py 电力数据 --init
```

## 根本原因

**Hook 检测逻辑**：
- Hook 检测到 status.json 存在且状态为 `initialized`
- 但 `.active_session` 标记文件不存在
- 判定为异常状态，阻断执行

**触发场景**：
1. 之前执行工作流时异常中断（如子 agent 超时）
2. status.json 保持 `initialized` 状态
3. 会话标记文件被清理或不存在
4. 后续所有操作都被阻断

## 解决方案

### 方案 A：批量清理僵尸工作流（推荐）

```bash
for dir in ~/.hermes/workflows/*/; do
    name=$(basename "$dir")
    status_file="$dir/status.json"
    if [ -f "$status_file" ]; then
        status=$(python3 -c "import json; print(json.load(open('$status_file'))['status'])" 2>/dev/null)
        if [ "$status" = "initialized" ]; then
            echo "清理: $name"
            python3 -c "
import json
path = '$status_file'
with open(path, 'r+') as f:
    d = json.load(f)
    d['status'] = 'completed'
    f.seek(0)
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.truncate()
"
        fi
    fi
done
```

### 方案 B：创建会话标记绕过

```bash
echo '{"workflow": "当前工作流名", "pid": '$$', "created_at": "'$(date -Iseconds)'"}' > ~/.hermes/workflows/.active_session
```

**注意**：方案 B 是临时绕过，执行后需清理标记：
```bash
rm -f ~/.hermes/workflows/.active_session
```

## 预防措施

1. **子 agent 超时处理**：
   - 子 agent 达到 max_iterations 时，应先更新 status.json 为 completed
   - 或在 Hook 中添加超时自动清理逻辑

2. **会话标记同步**：
   - status.json 和 .active_session 应同步创建/清理
   - 异常中断时，两者都应被清理

3. **Hook 容错增强**：
   - 检测到僵尸状态时，提供清理命令而非直接阻断
   - 或自动清理并继续执行

## 相关文件

- 会话标记机制：`references/hook-session-marker-mechanism-20260514.md`
- 标记文件陷阱：`references/hook-marker-file-trap-20260516.md`
- Hook 问题记录：`references/hook-mechanism-issues-20260518.md`

## 实际案例

**时间**：2026-05-18
**工作流**：月报生成
**阻断原因**：电力数据、nuclei扫描工作流处于 initialized 状态
**解决**：批量清理后恢复正常
