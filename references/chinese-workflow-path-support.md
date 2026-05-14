# 中文工作流路径支持方案

## 问题

终端工具限制中文字符路径，但所有工作流都是中文命名。

## 解决方案

### 1. execute.py 增加 --path 参数

**修改位置**：`actions/execute.py`

**关键改动**：
```python
def find_workflow_dir(workflow_name: str, workflow_path: str = None) -> Path:
    # 0. 如果提供了完整路径，直接使用
    if workflow_path:
        path = Path(workflow_path)
        if path.exists() and (path / 'WORKFLOW.md').exists():
            return path
```

**参数说明**：
- `--path`：工作流完整路径（支持中文路径）

### 2. handler.sh 支持路径参数

**修改位置**：`hooks/workflow-ai-remind/handler.sh`

**关键改动**：
```bash
# 支持路径参数
WORKFLOW_PATH="$1"

# 0. 如果提供了路径参数，直接使用
if [ -n "$WORKFLOW_PATH" ]; then
    if [ -f "$WORKFLOW_PATH/status.json" ]; then
        WORKFLOW_DIR="$WORKFLOW_PATH"
    fi
fi
```

### 3. 使用方法

**初始化工作流**：
```bash
python execute.py 工作流名称 --init --path "/完整路径"
```

**注入约束**：
```bash
bash handler.sh "/完整路径"
```

**示例**：
```bash
python execute.py 测试套件 --init --path "/x/AI/openclaw/workflows/测试套件"
bash handler.sh "/x/AI/openclaw/workflows/测试套件"
```

## 测试验证

**测试工作流**：
- 测试-普通工作流：✅ 通过
- 测试-断点工作流：✅ 通过（断点位置标注正确）
- 测试套件：✅ 通过（子工作流列表正确）

## 实施日期

2026-05-13
