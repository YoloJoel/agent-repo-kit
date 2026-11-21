# 质量评测协议

rc.3 的当前实现/资格见 [quality-status.md](quality-status.md)。以下记录协议与边界，不预填真实模型分数。

运行 `python hack/ai/assets/quality_trial.py <manifest.json> --output <report.json>` 校验成对实测记录。
仓内开发也可直接运行 `src/agent_repo_kit/assets/quality_trial.py`。输入均相对 manifest 所在目录，
`inputs` 保存每个原始文件的 SHA256；判定不能仅提交汇总分数。

| manifest 字段 | 内容 |
| --- | --- |
| schema_version / source_revision | 1 / 冻结源码版本，另在 inputs 保存实际源码快照摘要与任务材料 |
| protocol / reference | 预先冻结的 JSON 协议与独立事实参照路径；协议保存相同 source_revision、dataset、release_gate |
| dataset | split 为 development 或 holdout；case_ids 是独立建立的完整分母 |
| inputs | 所有输入、Spec、预测、裁定、原始执行日志的文件路径→SHA256 |
| runs | 每个 method(manual/kit)、stage(initial/source-audit/recheck)、repeat 的原始记录 |
| runs.settings | model、model_version、host、tool_permissions、context_budget、generation_budget；同一对必须相同 |
| runs 的产物 | spec、execution_log、predictions、judgments 路径；review_mode 明确 same-agent-separate-pass 或 separate-context-attested |
| predictions | answers，每个 id 有 status 和 expected；无法推导时记录 ambiguous，而不是猜测 |
| judgments | predictions_sha256 和 rows；每个 id 的 result、reason、evidence、observed；result 为 entailed/contradicted/ambiguous/unasked/source-unknown |
| runs.cost | wall_seconds、input_tokens、output_tokens、manual_minutes、reminders、repair_rounds、false_blocks；缺失不能填 0 冒充测得 |
| release_gate | 预先确定 minimum_entailed_ratio 和 minimum_repeats；关键项零缺口；不能读完结果后改门槛 |

输出分开显示 accounting status、各阶段分母/结果/成本、每组成对差值和 product_quality。
开发集、补审成绩、缺初稿、混模型预算、缺分母或缺成本不能冒充初稿留出集资格。
评测器核对所提供记录的一致性；不能验证日志来源真实性、阅读上下文隔离或裁定者的语义判断。
产品发布还必须满足真实连续变更、关键反例及宿主/运行环境的验收，不能由该文件的 PASS 单独批准。

模块 M 的下一次对比应冻结相同 R1–R8 范围、同一人工 baseline 与 Kit 初稿，并由不看作者标签的
读者回答同一组独立问题。报告分别列事实错误、遗漏、不可推导、矛盾、外部待验和成本；
上述真实材料尚未在当前修复输入中提供，公开夹具不得替代这项结果。

评测同时看生成产物与后续修改结果，禁止把文件数、格式 PASS、测试 ID 数和审计次数当成语义分数。

| 评测层 | 输入和观察 | 输出 |
| --- | --- | --- |
| 确定性反例 | 缺行为、横切遗漏、定义代替使用、猜测晋升、反证未闭、同条件契约冲突、注释代替断言、降级、漂移 | 检查是否准确拒绝/待定，合法差异是否误报 |
| 原生执行 | C/C++、Java、Python 实际命令；同一断言对正确/故意错误/恢复实现运行 | 构建和行为测试分别记录，缺工具 NOT_RUN |
| 模型任务 | 新会话只获得原始仓库、用户任务、发布 Skill | 原始源码保留、行为清单、实际规格、审计问题、测试结果、可接续状态 |
| 真实项目 | 不同规模/技术栈、已有资产/无规范仓；有意义的后续修改 | 从源码独立评审、实施前/后证据、剩余缺口和生产依赖 |
| 运行器与发行 | 已安装包、两个 Skills、升级/幂等/人工冲突，宿主加载与 Hook 分开 | 版本/内核哈希一致性、实际支持等级 |

`tests/test_behavior_quality.py` 是确定性反例，不是泛化业务评测；
`python tools/qualify_behavior.py --output <隔离证据目录>` 实际运行原生正反探针，
不会安装依赖。Java 需要可用 javac/java；只有 JRE 时保持 NOT_RUN。
CI 为该探针提供 JDK，运行结果以实际记录为准，配置不等于通过。

`examples/config-relay` 是可复现的小型跨模块项目，包含配置生效、去重、容量、
配置通知、设备断开和 best-effort 消息路径。用来暴露方法问题，不能替代大仓。
新仓/已有仓的模型任务必须隔离目录，不能向执行者泄露预期答案/问题清单。
评估者从实际源码独立建立参照行为，再对比产物；不得只沿生成文档自检。

每次记录：工具版本/内核哈希、原始输入提交与工作区哈希、任务、运行环境、
真正使用的命令/筛选范围/日志、产物、审阅方式、问题和复验、未运行条件。
指标分列：发现行为数、已复核/未知行为、规范条款映射、真实断言关联、实际执行范围、
跨规格冲突、失效知识、修复后重复问题、后续修改回归效果。行为覆盖分母是已发现清单，
仍需外部独立评审发现清单本身是否遗漏。不得给出无依据的“全仓理解百分比”。

开放待验收：私有大规模 C/C++/Java 工程、真实 Redis/DB/设备/协议依赖、长期多次
演进与各宿主可信 Hook。工具不访问用户内部源码，本轮输入摘要不能代替这些执行证据。

`examples/control-hub` 提供有实际注册表、配置路径、消息字段、规则顺序、窗口和信号的 C 项目。
`python tools/qualify_source_facts.py --output <隔离证据目录>` 在 Linux 上实际构建并运行这些路径，
核对实际的容量拒绝边界，再改变规则行为并复跑同一批原测试。
原测试对错误规则仍通过，记录的是断言缺口。每条观察对应实际输出，执行日志与哈希保留。
探针依赖 Linux 上的 cc、make、python3，缺条件按真实 NOT_RUN 记录。

模型任务从原始项目和实际安装的 Skill 开始，生成者看不到探针预期和审阅结论。
相同源码、测试和任务分别使用发行前后的安装资源。审阅者独立从源码核对最终条款、
缺陷处置和断言映射，并记录两版各自的问题。样例审阅和原生探针结果按各自范围报告。
