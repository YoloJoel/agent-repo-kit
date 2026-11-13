# agent-repo-kit

一次接入仓库工程规范。初始化和现状分析使用 Skill；日常开发自由使用 OpenSpec、其他 Skills 或直接对话。

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

0.2.0 默认只提供两个接入 Skill。日常开发入口自由，本地检查是基础；Plugin/Skills 安装、
原生 OpenSpec 两次交付与归档、存量 Java/Maven 仓的实施前验证和回归、0.1 升级均有实际记录。

- [新仓 / 存量仓 / 已有 OpenSpec 的使用方式](docs/getting-started.md)
- [实仓对标与最终验收](docs/acceptance.md)
- [本地反馈、可选 Git Hook 与其他流水线](docs/local-operation.md)
- [逐项支持和未实测边界](docs/compatibility.md)

自动检查验证可确定的结构、关联、状态和执行证据；业务解释、用例完整性及断言质量仍需源码分析和审阅。
