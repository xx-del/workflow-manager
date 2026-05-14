     1|# 实现要点
     2|
     3|## AI 自动化行为
     4|
     5|### 执行完成后自动生成历史摘要
     6|
     7|当工作流执行完成后，无论成功或失败，AI 必须自动执行以下操作：
     8|
     9|1. **读取结果** - 读取工作流输出
    10|2. **生成摘要** - 用自然语言描述执行结果
    11|3. **写入历史** - 记录到 `history/{日期}.json`
    12|
    13|### 示例
    14|
    15|```
    16|扫描完成！发现389个开放端口。
    17|
    18|[自动生成历史记录]
    19|→ 端口扫描 - 2026-03-17 - success - 扫描26个IP，发现389个开放端口
    20|```
    21|
    22|---
    23|
    24|## 自然语言理解映射
    25|
    26|| 用户输入 | 解析结果 |
    27||----------|----------|
    28|| "创建一个工作流" | 进入阶段1，生成草案 |
    29|| "测试一下" | 执行当前草案 |
    30|| "修改步骤2" | 修改草案步骤 |
    31|| "创建为工作流" | 进入阶段2，保存 |
    32|| "列出所有" | execute_workflow("list", {}) 直接输出返回的字符串 |
    33|| "执行电力数据" | 启动工作流 |
    34|| "查看状态" | 读取 status.json |
    35|| "停止工作流" | 调用 workflow-utils.sh stop |
    36|| "强制停止" | 调用 workflow-utils.sh stop force |
    37|| "重试" | 重置 retry 计数，重新执行 |
    38|| "定时每天6点" | 设置 cron 任务 |
    39|| "查看历史" | 列出 history/ 目录 |
    40|| "同步状态" | 调用 workflow-utils.sh sync |
    41|
    42|---
    43|
    44|## ⚠️ 执行工作流步骤的原则（重要）
    45|
    46|### 核心原则
    47|
    48|**工作流已定义的步骤 = 标准操作流程，不要自己重新设计！**
    49|
    50|### 正确做法
    51|
    52|1. **用户说"执行某工作流"** → 读取 WORKFLOW.md → 按步骤执行
    53|2. **用户说"执行某步骤"** → 读取 WORKFLOW.md → 找到对应步骤 → 执行该步骤的命令
    54|3. **用户说"检查状态"** → 读取 WORKFLOW.md → 找到状态检查相关的步骤 → 执行
    55|
    56|### 错误做法
    57|
    58|❌ 用户说"检查扫描进度" → 自己设计检查方案 → 执行自己设计的命令
    59|
    60|✅ 用户说"检查扫描进度" → 读取 WORKFLOW.md → 找到"步骤6: 查看AWVS扫描进度" → 执行工作流定义的命令
    61|
    62|### 执行前确认流程
    63|
    64|```
    65|1. 用户提出需求
    66|     ↓
    67|2. 阅读 WORKFLOW.md，找到对应步骤
    68|     ↓
    69|3. 告诉用户：我会执行步骤X和步骤Y，具体命令是...
    70|     ↓
    71|4. 用户确认同意
    72|     ↓
    73|5. 执行工作流定义的命令
    74|```
    75|
    76|### 为什么这样做
    77|
    78|- 工作流经过设计和验证，步骤清晰、命令正确
    79|- 自己设计容易遗漏细节、使用错误命令
    80|- 用户创建工作流就是为了标准化操作，应该信任它
    81|
    82|---
    83|
    84|## 守护 Agent 实现
    85|
    86|### 重要：守护Agent由主Agent直接启动
    87|
    88|**执行工作流时，主Agent同时启动守护Agent和执行Agent：**
    89|
    90|```
    91|步骤 1: 读取 WORKFLOW.md
    92|- 理解工作流目标和步骤
    93|
    94|步骤 2: 分析 guardian 配置
    95|- 检查 WORKFLOW.md 中的 guardian: true/false
    96|- 如果为 true，执行步骤 3
    97|
    98|步骤 3: 更新 status.json
    99|- status: "running"
   100|- started: 当前时间
   101|- guardian:
   102|    enabled: true
   103|    last_check: 当前时间
   104|    check_count: 0
   105|    last_status: "starting"
   106|    analysis: "工作流刚启动"
   107|
   108|步骤 4: 启动守护Agent（通过sessions_spawn）
   109|- 使用 workflow-guardian skill
   110|- 传入工作流路径
   111|- 守护Agent在后台周期性检查 + 更新状态
   112|
   113|步骤 5: 启动执行Agent（通过agent-pool）
   114|- 执行工作流步骤
   115|- 不需要关心状态更新
   116|
   117|步骤 6: 守护Agent周期性工作
   118|- 每5分钟检查一次
   119|- 更新 guardian 字段
   120|- 检测异常 → 修复或通知
   121|
   122|步骤 7: 工作流结束
   123|- 执行Agent更新 status (completed/failed)
   124|- 守护Agent检测到结束，自动停止
   125|```
   126|
   127|### 守护 Agent 生命周期
   128|
   129|```
   130|工作流开始 → 传递守护语义给 agent-pool → 自动生成守护 agent → 定期检查 → 检测停止信号 → 工作流结束 → 守护停止
   131|```
   132|
   133|### 守护 Agent 检查清单
   134|
   135|| 检查项 | 频率 | 动作 |
   136||--------|------|------|
   137|| **状态更新** | 每5分钟 | **必须更新guardian字段** |
   138|| 状态正常 | 每5分钟 | 记录正常 |
   139|| 卡住检测 | 每5分钟 | 如超过30分钟无更新 → 诊断/修复 |
   140|| 停止信号 | 每步骤前 | 检查 stop_requested / stop_force |
   141|| 失败检测 | 每5分钟 | 如失败 → 触发重试或通知 |
   142|
   143|**状态更新格式：**
   144|```json
   145|"guardian": {
   146|  "last_check": "2026-03-25T15:10:00Z",
   147|  "check_count": 2,
   148|  "last_status": "normal",
   149|  "analysis": "进程存在，日志有输出"
   150|}
   151|```
   152|
   153|### 实际执行命令
   154|
   155|```bash
   156|# 1. 读取工作流
   157|cat ~/.openclaw/workspace/workflows/{工作流}/WORKFLOW.md
   158|
   159|# 2. 检查 guardian 配置
   160|grep "guardian:" ~/.openclaw/workspace/workflows/{工作流}/WORKFLOW.md
   161|
   162|# 3. 更新状态
   163|echo '{"status": "running", "started": "'$(date -Iseconds)'"}' > ~/.openclaw/workspace/workflows/{工作流}/status.json
   164|
   165|# 4. 启动 agent（传递守护语义）
   166|sessions_spawn 任务描述+守护语义
   167|```
   168|
   169|---
   170|
   171|## 核心功能实现
   172|
   173|### 0. 停止工作流（新增）
   174|
   175|当用户请求停止工作流时：
   176|1. 读取当前 status.json
   177|2. 更新 `stop_requested: true`
   178|3. 可选设置 `stop_force: true` 强制立即停止
   179|
   180|**用户说"停止"时的自动行为：**
   181|```
   182|用户: "停止工作流"
   183|  ↓
   184|读取 workflows/{工作流}/status.json
   185|  ↓
   186|更新: stop_requested = true
   187|  ↓
   188|通知: "已收到停止请求，工作流将在当前步骤完成后停止"
   189|```
   190|
   191|**执行循环中的停止检查（每个步骤前）：**
   192|```
   193|读取 status.json
   194|  ↓
   195|if stop_force == true:
   196|  status = "stopped"
   197|  从 _running.json 移除
   198|  通知: "工作流已强制停止"
   199|  退出执行
   200|  ↓
   201|if stop_requested == true:
   202|  status = "stopping"
   203|  ↓
   204|  当前步骤完成后:
   205|    status = "stopped"
   206|    stopped_at = 当前时间
   207|    从 _running.json 移除
   208|    通知: "工作流已停止"
   209|    退出执行
   210|```
   211|
   212|### 1. 创建工作流
   213|
   214|1. 理解用户需求
   215|2. 生成 WORKFLOW.md 草案（粗粒度）
   216|3. ⭐ 自动检查并细分步骤（见 1.3）
   217|4. 写入工作流目录
   218|5. 注册到索引
   219|
   220|### 1.3 ⭐ 自动检查并细分步骤
   221|
   222|在写入工作流之前，必须自动检查步骤粒度并进行细分。
   223|
   224|**检查标准：**
   225|- 步骤数 < 5 → 需要细分
   226|- 单一步骤包含多个操作（如"下载并分析"）→ 需要拆分
   227|- 缺少验证步骤 → 需要添加
   228|- 缺少 Agent要求 标注 → 需要添加
   229|
   230|**细分原则：**
   231|- 每个"执行"步骤后添加"验证"步骤
   232|- 每个步骤标注 Agent要求
   233|- 确保每步骤独立、不累积上下文
   234|- 遵循"每步骤专属Agent"设计理念
   235|
   236|**细分模板：**
   237|
   238|原始粗粒度：
   239|:   ### 步骤1: 下载JSON文件
   240|    **做什么**: 下载并分析JSON数据
   241|    **执行指令**: bash download.sh
   242|
   243|细分为：
   244|:   ### 步骤1.1: 执行下载
   245|    **做什么**: 下载JSON文件
   246|    **执行指令**: bash download.sh
   247|    **Agent要求**: CLI执行
   248|
   249|    ### 步骤1.2: 验证下载成功
   250|    **做什么**: 检查文件是否完整
   251|    **执行指令**: if [ -f output.json ] && [ -s output.json ]; then echo "OK"; fi
   252|    **Agent要求**: CLI执行
   253|
   254|**操作流程：**
   255|
   256|```
   257|1. 生成 WORKFLOW.md 草案
   258|   ↓
   259|2. 检查步骤数量
   260|   ├─ 步骤数 >= 5 → 继续检查粒度
   261|   └─ 步骤数 < 5 → 细分步骤
   262|   ↓
   263|3. 检查步骤粒度
   264|   ├─ 单步骤是否包含多个操作？
   265|   ├─ 是否有验证步骤？
   266|   └─ 是否有 Agent要求 标注？
   267|   ↓
   268|4. 如需细分
   269|   ├─ 拆分粗粒度步骤为"执行+验证"对
   270|   ├─ 为每个步骤添加 Agent要求
   271|   └─ 更新 WORKFLOW.md
   272|   ↓
   273|5. 验证细分结果
   274|   └─ 确保每步骤独立、最小化
   275|```
   276|
   277|### 2. 执行工作流（核心）
   278|
   279|> ⚠️ **必须通过 agent-pool 执行，禁止直接执行命令**
   280|
   281|**执行流程（v3.8 - 节点展开版）**：
   282|
   283|```
   284|1. 解析用户请求（"执行漏扫"）
   285|   ↓
   286|2. 读取 _index.yaml（获取节点列表）
   287|   ↓
   288|3. ⭐ 思考分析阶段（v3.8）
   289|   ├─ 节点类型分析（判断并展开串联节点）← 新增
   290|   ├─ 任务类型分析（CLI/AI/混合）
   291|   ├─ 依赖关系分析（串行/并行）
   292|   ├─ Agent分配策略
   293|   └─ 风险预判
   294|   ↓
   295|4. ⭐ 制定分配方案（轻量级）
   296|   ├─ 哪些任务可以并行？
   297|   ├─ 哪些任务需要特定技能？
   298|   ├─ 哪些任务可以复用agent？
   299|   └─ 资源分配（3个agent并发限制）
   300|   ↓
   301|5. 写入 _running.json（标记工作流开始）
   302|   ↓
   303|6. 更新 status.json（状态: running）
   304|   ↓
   305|7. 指挥 agent-pool 执行
   306|   ├─ 传递任务列表（展开后）
   307|   ├─ 传递分配策略
   308|   └─ 传递并发约束
   309|   ↓
   310|8. 传递 guardian_semantic 给 agent-pool（含停止检查逻辑）
   311|   ↓
   312|9. 监控 agent 执行状态（含停止信号检查）
   313|   ↓
   314|10. 汇总结果，更新状态
   315|   ↓
   316|10. 从 _running.json 移除
   317|```
   318|
   319|**具体步骤：**
   320|
   321|```
   322|1. 读取 _index.yaml，获取节点列表（nodes）
   323|
   324|2. ⭐ 思考分析阶段（v3.8）
   325|   ┌─────────────────────────────────────────────────────┐
   326|   │ [节点类型分析] ← 新增：判断并展开串联节点          │
   327|   │ - 判断每个节点的 calls 字段                       │
   328|   │ - calls = workflow-manager → 展开为实际步骤        │
   329|   │ - calls = agent-pool → 直接作为任务               │
   330|   │ - 输出：展开后的任务列表                           │
   331|   │                                                   │
   332|   │ [任务类型分析]                                    │
   333|   │ - 哪些是CLI任务？（确定性高）                     │
   334|   │ - 哪些是AI任务？（需要推理）                      │
   335|   │ - 哪些是混合任务？（需要协调）                    │
   336|   │ - 输入：展开后的任务列表                          │
   337|   │                                                   │
   338|   │ [依赖关系分析]                                    │
   339|   │ - 哪些任务必须串行？（数据依赖）                  │
   340|   │ - 哪些任务可以并行？（无依赖）                    │
   341|   │ - 关键路径是什么？                                │
   342|   │ - 输入：展开后的任务列表                          │
   343|   │                                                   │
   344|   │ [Agent分配策略]                                   │
   345|   │ - 默认策略：每步骤专属Agent（推荐）               │
   346|   │ - 输入：展开后的任务列表                          │
   347|   │ - 输出：任务分配矩阵                              │
   348|   │                                                   │
   349|   │ [风险预判]                                        │
   350|   │ - 哪些任务可能失败？                              │
   351|   │ - 失败后如何重试？                                │
   352|   │ - 超时如何处理？                                  │
   353|   └─────────────────────────────────────────────────────┘
   354|
   355|3. 制定分配方案（每步骤专属Agent）
   356|   - 输出：任务分配矩阵
   357|   - 原则：每步骤至少一个专属Agent
   358|   - 示例：
   359|     {
   360|       "agent_1": ["步骤1"],
   361|       "agent_2": ["步骤2"],
   362|       "agent_3": ["步骤3"],
   363|       "agent_4": ["步骤4"],
   364|       "agent_5": ["步骤5"]
   365|     }
   366|   - 约束：
   367|     - 串行步骤：按序执行，每个步骤独立Agent
   368|     - 并行步骤：可并行执行，每步骤独立Agent
   369|     - 步骤间通过数据文件传递，不通过上下文
   370|   - 注意：子Agent内部需要并行分析时，保持现有机制不变
   371|
   372|4. 写入 _running.json:
   373|   workflows/_running.json
   374|   └── {工作流ID}: {status: running, started: 时间}
   375|
   376|5. 更新 status.json:
   377|   - status: "running"
   378|   - started: 当前时间
   379|   - stop_requested: false
   380|   - stop_force: false
   381|
   382|6. 调用 agent-pool，传递：
   383|   - 任务描述：执行 {工作流名称}
   384|   - 步骤列表：每个步骤的执行指令
   385|   - 分配策略：任务分配矩阵（新增）
   386|   - 并行策略：哪些步骤可以并行
   387|   - 守护语义：guardian_semantic（含停止检查）
   388|   - 并发约束：最多3个agent（新增）
   389|
   390|7. agent-pool 根据分配策略生成执行 agent
   391|
   392|7. 执行循环中每个步骤前检查停止信号
   393|
   394|9. 执行完成后汇总结果
   395|
### 8. ⭐ 节点验证（v3.10 新增）

**触发时机**：每个节点执行完成后，执行下一节点前

**验证流程**：

```
[节点执行完成]
     ↓
[1] 读取节点定义
     ├─ 输出文件列表
     ├─ 完成条件
     └─ 输出格式定义
     ↓
[2] 存在性检查
     └─ 所有输出文件是否存在？
     ↓
[3] 非空性检查
     └─ 如完成条件要求"非空"，检查文件大小
     ↓
[4] 格式检查
     └─ 如有格式定义，验证文件格式
          - url_list: 每行是否为URL
          - json: 是否为有效JSON
          - markdown: 是否为Markdown
     ↓
[5] 更新验证状态
     └─ 写入 status.json
     ↓
[6] 处理验证结果
     ├─ 通过 → 继续下一节点
     └─ 失败 → 停止工作流，触发通知
```

**验证失败处理**：

```
节点验证失败
     ↓
[1] 停止工作流执行
[2] 更新 status.json
     ├─ status = "node_validation_failed"
     ├─ failed_node = {node_id}
     └─ validation_errors = [错误列表]
[3] 触发通知
[4] 等待用户确认
```

**节点验证伪代码**：

```python
def validate_node_outputs(node_id, workflow_path):
    """节点完成后自动验证"""
    
    # 1. 读取节点定义
    node = read_node_definition(workflow_path, node_id)
    output_files = node.get("输出", [])
    completion_condition = node.get("完成条件", "")
    output_format = node.get("输出格式", {})
    
    validation_result = {
        "passed": True,
        "checks": [],
        "errors": []
    }
    
    # 2. 文件存在性检查
    for output_file in output_files:
        file_path = resolve_output_path(output_file)
        
        check = {"file": output_file}
        
        # 存在性
        check["exists"] = os.path.exists(file_path)
        if not check["exists"]:
            validation_result["passed"] = False
            validation_result["errors"].append(f"{output_file} 不存在")
        
        # 非空检查（如完成条件要求）
        if "非空" in completion_condition and check["exists"]:
            check["non_empty"] = os.path.getsize(file_path) > 0
            if not check["non_empty"]:
                validation_result["passed"] = False
                validation_result["errors"].append(f"{output_file} 为空")
        
        # 格式检查（如有定义）
        if check["exists"] and output_file in output_format:
            format_type = output_format[output_file]
            check["format_correct"] = validate_file_format(file_path, format_type)
            if not check["format_correct"]:
                validation_result["passed"] = False
                validation_result["errors"].append(f"{output_file} 格式不正确，期望 {format_type}")
        
        # 统计行数
        if check["exists"]:
            check["line_count"] = count_lines(file_path)
        
        validation_result["checks"].append(check)
    
    # 3. 更新 status.json
    update_node_validation(workflow_path, node_id, validation_result)
    
    # 4. 处理验证结果
    if not validation_result["passed"]:
        raise NodeValidationError(f"节点 {node_id} 验证失败: {validation_result['errors']}")
    
    return validation_result
```

---


   396|9. 更新 status.json: status = "completed" / "failed" / "stopped"
   397|
   398|10. 从 _running.json 中移除该工作流
   399|```
   400|
   401|**_running.json 格式：**
   402|```json
   403|{
   404|  "version": "1.0.0",
   405|  "updated": "2026-03-24T10:00:00Z",
   406|  "workflows": {
   407|    "资产收集流程": {
   408|      "status": "running",
   409|      "started": "2026-03-24T10:37:00Z",
   410|      "progress": "4/5"
   411|    },
   412|    "端口扫描": {
   413|      "status": "running",
   414|      "started": "2026-03-24T11:00:00Z",
   415|      "progress": "1/3"
   416|    }
   417|  }
   418|}
   419|```
   420|
   421|**_running.json 同步时机：**
   422|| 阶段 | 操作 |
   423||------|------|
   424|| 工作流启动时 | 写入 workflows/{ID} |
   425|| 状态变更时 | 更新 progress |
   426|| 完成/失败/停止时 | 从 workflows/{ID} 删除 |
   427|
   428|### 3. 思考分析阶段详解（v3.8 重构）
   429|
   430|**目的**: 在执行前分析任务，制定最优的agent分配策略
   431|
   432|**不是制定完整的执行方案**（WORKFLOW.md 已经定义了），而是思考如何最优分配agent任务。
   433|
   434|---
   435|
   436|#### 3.0 节点类型分析（v3.8 新增）⚠️（核心）
   437|
   438|**目的**: 在分析任务类型之前，先判断节点类型，展开串联工作流节点。
   439|
   440|**核心原则**: 工作流节点分为"直接执行节点"和"串联调用节点"。
   441|
   442|---
   443|
   444|##### 节点类型判断
   445|
   446|从 _index.yaml 中读取工作流节点，根据 `calls` 字段判断节点类型：
   447|
   448|| 节点 calls 字段 | 节点类型 | 处理方式 |
   449||----------------|----------|----------|
   450|| `agent-pool` | 直接执行节点 | 作为1个任务 |
   451|| `workflow-manager` | 串联调用节点 | ⭐ 需要展开为实际步骤 |
   452|
   453|---
   454|
   455|##### 串联节点展开逻辑
   456|
   457|**当节点 calls = "workflow-manager" 时**:
   458|
   459|```
   460|1. 根据 node.name 查找被串联的工作流
   461|   - 在 _index.yaml 中搜索 name 匹配的工作流
   462|   - 获取该工作流的 path
   463|
   464|2. 读取被串联工作流的 _index.yaml
   465|   - 路径: {path}/_index.yaml 或 workflows/{工作流名}/_index.yaml
   466|   - 提取该工作流的 nodes 字段
   467|
   468|3. 遍历被串联工作流的 nodes
   469|   - 为每个 node 生成 Agent 任务
   470|   - 任务名格式: "{父工作流}/{子步骤}"
   471|   - 例如: "凭证检测/验证输入文件"
   472|
   473|4. 汇总到总任务列表
   474|   - 所有串联节点的展开任务合并为一个列表
   475|   - 保持原有顺序（先凭证检测的所有步骤，再Home漏扫的所有步骤...）
   476|```
   477|
   478|---
   479|
   480|##### 节点展开示例：通用漏洞扫描
   481|
   482|**原始工作流节点**:
   483|```yaml
   484|nodes:
   485|- id: 1
   486|  name: 凭证检测
   487|  calls: workflow-manager  # 串联节点
   488|- id: 2
   489|  name: Home漏扫
   490|  calls: workflow-manager  # 串联节点
   491|- id: 3
   492|  name: 爆破测试
   493|  calls: workflow-manager  # 串联节点
   494|- id: 4
   495|  name: 漏扫
   496|  calls: workflow-manager  # 串联节点
   497|```
   498|
   499|**展开过程**:
   500|```
   501|