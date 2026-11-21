# agent-repo-kit

一次接入仓库工程规范。初始化和现状分析使用 Skill；日常开发自由使用 OpenSpec、其他 Skills 或直接对话。

本分支为 **0.4.0-rc.3** 行为质量修复候选：增加独立源码候选、完整 Scenario 绑定、冻结回读和实际 case 执行证据。当前能力与待验范围统一见[质量状态](docs/quality-status.md)，八轮实施与结果见[修复计划](docs/iterations/quality-repair-program.md)。Marketplace 暂仍固定在 rc.2；工程通过不代表已达到人工 baseline 的生成质量。

现状分析按行为批次先记录源码事实，再写条款、核对实际断言并重读源码。
注册/命令字面量、实际校验边界、时序触发、策略优先级和最后生效的生命周期处理都要有决定性证据。
已有资产和证据协议继续复用，缺陷、未知项和缺断言保留实际状态。
详见 [生成质量修订](docs/repairs/source-facts-0.3.1.md) 和 [质量评测协议](docs/evaluation.md)。

本轮统一修复运行期输入失效、复合需求依赖、原生归档交接、相对执行器就绪诊断和断言位置判断，
并完成源码/既有资产接入与升级的发布前验证。实际结果与边界见 [0.3.2 发布前收口](docs/repairs/pretest-readiness-0.3.2.md)。

## 安装与首次接入

Claude Code 原生 Plugin：

```text
/plugin install agent-repo-kit --marketplace YoloJoel/agent-repo-kit
/agent-repo-kit:initialize-repo
```

其他运行器通过标准 Skills 安装，例如 Codex：

```bash
npx skills@1.8.1 add YoloJoel/agent-repo-kit --skill "*" -a codex -g
```

然后在业务仓调用 `$initialize-repo`。OpenCode 使用 `-a opencode` 并调用 initialize-repo。
套件默认提供两个 Skill：initialize-repo 接入仓库；baseline-repo 整理或更新源码现状。
初始化助手和资源随 Skill 打包。执行内核需要 Python 3.11+ 标准库；正常使用无需 pip、全局 ark、额外源码下载、常驻服务或 MCP。

## 日常开发

继续使用你选择的开发工具。仓内 AGENTS、工程规范和本地检查维护共同要求，不要求 deliver-change、手写 ark.json 或另一套 Change 生命周期。

- OpenSpec：复用原生 proposal、specs、tasks、可选 design 和原生归档；同步由原生工具负责。
- 其他工具：通过 `.ai/policy.json` 映射规格和变更目录，复用普通文档。
- 直接对话：Agent 按风险补齐必要资产，使用项目真实测试命令。
- 文案/机械修改：采用有理由、绑定内容的轻量记录，不强制完整 Change。

活动变更的 delta 是拟议行为；原生归档后检查当前 Spec 的同步。校验器不会把目标方案当成现状，也不替原生工具合并 delta。

## 不依赖托管平台或 CI

业务仓可以位于 GitLab、Gitee、内部 Git 服务，或仅保留本地工作目录。所有核心检查在本地执行：

```bash
python hack/ai/ark.py doctor
python hack/ai/ark.py check
python hack/ai/ark.py check --base <提交或分支>
```

由 Agent 使用这些仓内命令，用户无需记忆 CLI。必需业务命令在 policy.checks 中确认，未运行、缺失、失败或过期证据不能汇总成完整交付 PASS。
没有远端或 CI 不影响核心使用。CI 可以调用同一入口增强独立复验，初始化默认不生成 GitHub Actions；仅明确选择 `--ci github` 时生成。远端合并约束需另外配置，未配置不能宣称存在。

## 仓内资产

| 位置 | 职责 |
| --- | --- |
| AGENTS.md / CLAUDE.md | 核心规则和导航，保留人工内容 |
| docs/engineering-standard.md | 工作要求与完成标准 |
| docs/baseline/ | 模块、契约、来源、覆盖和缺口 |
| docs/adr/ | 长期架构决策 |
| openspec/specs/ | 当前有效行为 |
| openspec/changes/ | 原生或普通文件组织的计划与历史 |
| .ai/policy.json | 路径映射、真实验证命令和适用规则 |
| hack/ai/ | 可独立执行的仓内检查内核 |
| .ai/runtime/ | 被忽略的执行日志、证据和工作区缓存 |

初始化保留原规则、现有 OpenSpec、CI、编号及脏文件；重复执行保持幂等。源码盘点、Agent 静态分析和真实测试执行分别报告。

## 开发与验证

```bash
python -m pip install -e .
python tools/build_native.py
python tools/build_native.py --check
python -m unittest discover -s tests -v
```

原生发布目录 skills/ 从 assets/skills/*/WORKFLOW.md、内核和资源生成。不要手改生成副本。

[架构](docs/architecture.md) · [CLI](docs/cli.md) · [支持状态](docs/compatibility.md) · [迭代计划](docs/roadmap.md) · [执行记录](docs/iterations/IT-01.md)

## 完成状态与使用说明

以下为历史版本能力记录；本节记录截至 0.3.2 的能力，生成质量与评测边界见上方链接。

0.2.4 默认只提供两个接入 Skill。日常开发入口自由，本地检查是基础；Plugin/Skills 安装、
原生 OpenSpec 两次交付与归档、存量 Java/Maven 仓的实施前验证和回归、0.1 升级均有实际记录。

- [新仓 / 存量仓 / 已有 OpenSpec 的使用方式](docs/getting-started.md)
- [实仓对标与最终验收](docs/acceptance.md)
- [本地反馈、可选 Git Hook 与其他流水线](docs/local-operation.md)
- [逐项支持和未实测边界](docs/compatibility.md)

自动检查验证可确定的结构、关联、状态和执行证据；业务解释、用例完整性及断言质量仍需源码分析和审阅。

0.2.1 修复配置变更漏检、有效规格失去测试关联和说明过期仍通过交付的问题。
未知文件保守检查，受影响的知识需复核；已有仓使用更新后的 initialize-repo 显式升级。

0.2.2 的存量仓接入默认从 Baseline 继续生成或复用有源码依据的当前行为 Spec，
不需要额外提示词或预先运行 OpenSpec。缺陷/未知项单列，缺少测试保持验证 PENDING。
OpenSpec CLI 的安装及原生命令初始化仍是独立步骤。

0.2.3 在生成 Baseline/spec 后默认重新从源码复核：先从代码重建覆盖清单，
双向检查遗漏与错误，记录问题并处理，再重新打开源码复核修复和相邻路径。
审计记录绑定源码、产物和报告；未解决或过期保持 PENDING，不能用格式检查代替语义复核。

0.2.4 将 AGENTS 生成为项目化的七段入口，完整构建清单留在上下文；
存量接入按主要业务能力建立覆盖图，spec 正文须能脱离 Baseline 独立理解和验收。
Agent 使用 onboarding-status 汇总当前入口、全仓范围、规格和审计质量，局部 PASS 不代表全仓完成。
初始化报告是带时间的历史快照；编译结果与业务测试结果分别报告。
