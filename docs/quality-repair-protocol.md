# rc.3 行为质量协议与迁移

保留 schema_version 1 的旧记录可读性。缺少新证据的记录保持 PENDING，不自动补出审阅或执行。
现有仓升级后按 `baseline next` 处理受影响范围；保留已有 Spec、ID、ADR、原始锚点和历史。
runtime/Skill 更新使用原有显式 upgrade 和人工内容冲突流程，未更改全局宿主信任设置。

| 任务 | 命令 | 权威输入/结果 |
| --- | --- | --- |
| 当前待办 | `ark baseline next` | 从现有登记、Spec、审计和回读派生；不另建任务台账 |
| 独立发现 | `ark baseline discover` | 只读生产源码；原始候选状态 PENDING 是预期结果 |
| 发现对账 | `ark baseline discovery-record --document review.json --reviewer name` | 明确候选处置和来源；status 检查新候选与过期项 |
| 回读 | `ark baseline readback-open/predict/judge` | 见随包 baseline-repo/references/readback.md |
| 当前回读 | `ark baseline readback-status` | 当前活动轮次；`--id` 查看不可覆盖的旧轮次 |
| 查询 | `ark explain REQ-ID` / `ark explain BEH-ID` / `ark explain change-id` | 源码、Spec、断言、依赖、目标、ADR 引用、执行时效和缺口；只读 |
| 规则复核 | `ark rules record --reviewer name` / `ark rules status` | 已配置 artifact_rules 的源文件与规则内容同时绑定 |
| 跨仓快照 | `ark external record --document external.json --reviewer name` / `ark external status` | 仅显式本地绝对根与文件；不隐式联网、扫描整个外仓或归档外仓 |

跨仓映射示例：

```json
{"dependencies":[{"alias":"upstream","root":"/absolute/repository","files":["openspec/specs/protocol/spec.md"]}]}
```

同名文件用 `alias::path` 消歧。快照不可变，现行映射与外部文件变化使校验待审并改变交付指纹。
部署态、不可访问的外部消费者、移除/变更外部承诺仍需各仓原生 Change 和联合验收。

新执行协议：check 可声明 `case_report: {format: junit|ark-json, required_cases:[...]}`。
命令使用 `{case_report}` / ARK_CASE_REPORT 输出本轮报告；ARK JSON 还绑定 ARK_RUN_ID。
支持的 Python 命令自动记录实际断言行；复杂框架、并行子进程或其他语言使用原生报告。
behavior-plan 的 `observations: {check-name:[case-id]}` 指定每项保持/目标真正要求执行的观察。
旧 preserve fixtures 至少要求每个文件有断言实际通过，不能证明文件内所有分支已测试。
普通构建命令保持命令级契约。原测试命令语义不支持时保持待验，不静默换成推测命令。

Scenario 绑定新增完整块 name/sha256，包含 WHEN、THEN、表格和 fenced 输出，忽略 fenced 伪标题。
acceptance_cases 新增实际决定前提 premises。升级时重新审阅缺失的前提与场景，不能机械批量填 PASS。
共享 contract_catalog 负责明确别名和等价条件；未自动推断同义词。单元级过期保留无关单位统计，
新增未知文件仍使总体待审。老记录没有细粒度输入时保守失效，重新审阅后获得细粒度记录。

验收与恢复使用原生 Change。`explain` 不修改任何文件；`baseline next` 不自动循环执行，也不
要求用户逐批批准。source-audit 状态展示逐轮新增/重开/关闭和重复未解提示，帮助识别卡住原因。

运行器限制：源码扫描不是完整静态分析；断言行观测不是测试充分性；JUnit 的新路径不能阻止
执行器主动复制旧报告；reviewer 身份不能证明独立上下文。这些限制必须随实际成绩一起报告。
