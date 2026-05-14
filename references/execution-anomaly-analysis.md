# 工作流执行异常分析方法

## 核心原则：基于实际配置分析，不预设假设

**错误模式**：预设文件名/路径 → 检查发现不存在 → 错误结论"文件缺失"
**正确模式**：读取配置文件 → 确认实际配置 → 验证文件是否存在 → 分析执行日志

---

## 分析步骤

```
1. 读取配置文件，确认实际配置
   - 检查 config.py / settings.yaml 等配置文件
   - 确认文件路径、参数名称的实际值
   
2. 读取 WORKFLOW.md，确认步骤定义
   - 检查哪些步骤是必需的
   - 检查哪些步骤是验证性的
   
3. 分析代码执行逻辑
   - 静默跳过 vs 报错终止
   - 异常处理方式
   
4. 分析执行时间约束
   - delegate_task timeout 限制
   - 实际执行时间 vs 预期执行时间
   
5. 检查执行日志
   - debug.log / execution_log.txt
   - 检测阶段是否完成
   - 是否有中断信号
```

---

## 常见问题模式

| 问题类型 | 症状 | 根因分析方法 |
|----------|------|--------------|
| 执行时间异常短 | 结果不完整、步骤跳过 | 检查 delegate_task timeout 设置 |
| 静默跳过功能 | 配置存在但功能未执行 | 检查代码逻辑中的静默跳过条件 |
| 配置/实际不符 | 文件"不存在"但实际存在 | 检查配置文件中的实际路径定义 |

---

## 案例：爆破测试执行异常分析

**症状**：result_cache.json 中有 0 条登录尝试（attempt），只有检测记录（detection）

### 分析过程

**步骤1：检查配置文件**
```python
# config.py 第21行
PASSWORD_FILE = "passwd.txt"  # 不是 password.txt
```

**步骤2：检查文件是否存在**
```bash
ls -la /x/rank/hwxinxisouji/liuliang/baopo/passwd.txt
# 存在，151 bytes，20个密码
```

**步骤3：检查 WORKFLOW.md**
- 无验证字典文件的步骤
- 直接执行 `uv run main.py`

**步骤4：分析代码逻辑**
```python
# main.py 第317-330行
if file_usernames and file_passwords:
    # 执行字典测试
    ...
else:
    logging.warning("未找到用户名或密码字典文件，跳过字典测试")
    # 静默跳过，不报错
```

**步骤5：分析执行时间**
- delegate_task timeout: 600秒
- 36个URL检测+爆破预期时间: >600秒
- 实际结果: 检测阶段未完成，爆破阶段未开始

### 结论

| 问题 | 原因 |
|------|------|
| 字典文件名 | 配置和文件都是 `passwd.txt`，没有问题 |
| WORKFLOW.md 验证步骤 | **没有验证字典文件的步骤**，直接执行代码 |
| 代码执行逻辑 | 代码会静默跳过缺失的字典，不会终止 |
| 0条登录尝试 | **子agent执行超时**，检测阶段未完成，爆破阶段未开始 |

---

## 修复建议

### 1. WORKFLOW.md 添加字典文件验证步骤

```markdown
### 步骤 X: 验证字典文件
**做什么**: 检查字典文件是否存在且非空

**执行指令**:
```bash
# 检查配置中的实际文件名
grep PASSWORD_FILE config.py
# 验证文件存在
ls -la passwd.txt username.txt
# 验证文件非空
wc -l passwd.txt username.txt
```

**失败处理**: 文件不存在或为空 → 终止工作流 → 报告用户
```

### 2. 代码中添加字典验证

```python
# 在 main.py 中添加验证
file_usernames = config.get_username_list()
file_passwords = config.get_password_list()

if not file_usernames:
    raise FileNotFoundError(f"用户名字典文件为空或不存在: {config.USERNAME_FILE}")
if not file_passwords:
    raise FileNotFoundError(f"密码字典文件为空或不存在: {config.PASSWORD_FILE}")
```

### 3. 增加子agent执行超时时间

```yaml
# 工作流配置
config:
  timeout: 1800  # 30分钟，足够完成36个URL的检测+爆破
```
