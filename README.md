# agent-repo-kit

Reusable skills, templates, hooks, and checks for AI-driven software development.

面向不同语言、技术栈和 Coding Agent 的仓库工程套件：**每仓初始化一次，后续由 Agent
按任务维护事实、规格、实现和验证证据。** 支持新仓、存量仓、已有部分 AGENTS/OpenSpec/CI
的仓库。Python 3.11+，运行时仅使用标准库，无模型 API、常驻服务或必需的 MCP。

## 安装与第一次使用

在本工具包的克隆目录安装一次：

```bash
python -m pip install .
ark --version
```

初始化一个业务仓库：

```bash
ark init /path/to/project
# 如需安装 Codex/Claude Hook 配置和 GitHub CI 模板：
ark init /path/to/project --hooks --ci github
ark --repo /path/to/project doctor
```

Windows 可以使用本机 Python/`py` 安装；后续 `ark` 命令相同。初始化自动识别新仓/存量仓，
也支持 `--mode new`、`--mode existing` 和 `--agents codex,claude,opencode`。

初始化完成后，让 Agent 继续执行 `initialize-repo`：确认真实检查命令，存量仓完成
`baseline-repo` 的源码取证；然后直接提出普通开发任务，由 `deliver-change` 接续。
CLI 的 PASS 只表示脚手架成功，**不会把目录生成冒充现状分析完成**。

初始化会将执行内核和资源放进业务仓库；即使没有安装全局命令，也可运行：

```bash
python hack/ai/ark.py doctor
python hack/ai/ark.py verify --phase structure
```

业务仓库可以和工具包分离、离线使用。新克隆不必重做基线分析；每台开发机需要自己的 Python，
若启用 Hook 还需让 `ark` 在 PATH 上并完成运行器的信任设置。

## 三个 Skill

| Skill | 交付内容 |
| --- | --- |
| `initialize-repo` | 识别现有资产、合并入口、安装模板/执行内核、确认检查与接入状态 |
| `baseline-repo` | 解释实际模块/完整流程、外部契约、状态与异常，记录源码证据/覆盖/缺口 |
| `deliver-change` | 分析影响、保留必要行为、规格/设计/实现/测试、同步与实际验证 |

Skill 源码位于 `src/agent_repo_kit/assets/skills/`。初始化复制到选择的运行器发现目录，
这些生成副本由清单看护；修改公共流程应在工具包中完成，再显式升级消费仓。
Skill 是模型执行的工作流，Python 内核负责确定性检查，两者职责分别清楚。

## 仓内资产

| 位置 | 用途 |
| --- | --- |
| `AGENTS.md` / `CLAUDE.md` | 简短规则入口；保留人工内容，兼容导入 |
| `.ai/policy.json` | 路径、技术栈检查、需求验证映射和 Hook 模式 |
| `.ai/manifest.json` | 套件版本、生成文件摘要 |
| `docs/engineering-standard.md` | 工作流程和完成条件；已有文档保留 |
| `docs/baseline/` | 现状解释、契约、问题、覆盖和原始证据 |
| `docs/adr/` | 长期架构选择及替代关系 |
| `docs/templates/` | 模块、契约、ADR、Change、规格和同步审查模板 |
| `openspec/specs/` | 当前有效行为承诺 |
| `openspec/changes/` | 进行中与归档的变更、任务、验证记录 |
| `hack/ai/` | 仓内可独立运行的执行内核及资源 |
| `.ai/notes/` | 有理由、有内容摘要的轻量修改声明 |
| `.ai/runtime/` | 被忽略的执行日志、锁、会话指针和本地证据 |

已有目录可通过 `policy.paths` 映射。初始化保留已有规范、原编号、OpenSpec 配置、CI 和
未提交内容；遇到受管理文件冲突会停止该次安装事务，不使用覆盖或整仓重置。

## 存量仓 Baseline

```bash
ark baseline inventory
# Agent 阅读实际源码、调用方、配置和测试，填写模块解释：
ark baseline review --document docs/baseline/modules/module.md \
  --files src/module.py tests/test_module.py --reviewer agent-name
ark baseline validate
```

模块解释须有 Purpose、Flow、State and failure、Evidence、Gaps，并引用真实
`path:L1-L20` 范围。盘点只生成路径/摘要和待核实状态，不能证明已理解行为。
静态核对、真正运行的测试和生产观察分开记录。保留 raw 历史批次，增量更新受影响的当前索引。

源码说明回答“当前怎样运行”；Spec 回答“承诺什么”；Change 回答“准备改变什么”。
缺陷、实现细节和模型推断都不能自动升级为永久契约。原始文档可复用，关键事实仍须核对源码。

## 后续开发

```bash
ark change new bounded-output --kind feature --scope src tests \
  --requirements REQ-OUTPUT-001
ark change activate bounded-output --session actual-session-id
# Agent 填写 proposal、design、tasks 和 delta；建立必要基线/测试后：
ark verify --phase ready --change bounded-output
# 实现、完成任务、同步当前 Spec 并审查实际行为差异：
ark change record-sync bounded-output --artifact docs/sync-review.md \
  --reviewer agent-name --method reviewed
ark verify --phase delivery --change bounded-output
ark change close bounded-output
```

优先复用已有 OpenSpec 工作流，工具包不会重新实现 delta 合并器。原生工具实际执行后用
`--method native`；没有原生工具时，Agent 可以明确同步文件并审查结果，使用 `reviewed`，
记录实际做法，不伪造 CLI 成功。删除的需求通过 `--remove-requirements` 声明为受影响需求的
子集，同时保留移除行为的验证和兼容性依据。

存量代码的 ready 验证会保存受影响范围的**实现前基线锚点**；随后代码变化不要求把历史证据
改写成新实现。当前 Baseline 仍会如实显示变化后的待复核区域。

纯文案/格式或经核实无行为变化的机械修改采用轻量路径：

```bash
ark note --scope src/format_only.py --kind mechanical \
  --reason 'Only whitespace formatting changed; observable behavior is unchanged.' \
  --reviewer agent-name
```

记录绑定具体文件摘要；CI 重跑已有确认的项目检查。声明理由仍需审查，脚本不以行数判断
语义。轻量路径不要求完整 Change、全仓扫描或为凑覆盖新增测试。

## 确认实际验证命令

初始 `checks` 为空，构建文件发现的命令只在 `command_candidates` 中展示。确认后配置：

```json
{
  "checks": [
    {
      "name": "unit",
      "type": "command",
      "argv": ["{python}", "-m", "unittest", "discover", "-s", "tests"],
      "cwd": ".",
      "required": true,
      "timeout": 300
    }
  ]
}
```

这是策略文件中的片段，保留其他字段。Java/Go/Node/C 等项目使用其真实构建/测试命令；
不绑定某个语言或版本。参数数组不会通过 Shell 执行，`{python}` 指当前解释器。

单项状态为 PASS、FAIL、NOT_RUN；整体为 PASS、FAIL、PENDING。未配置行为检查、命令缺失、
未选中的必需检查、过期证据和必要外部验证未完成都不会得到交付 PASS。日志和输入摘要自动生成，
输入在检查期间改变会使验证失败。关闭 Change 还要求当前工作区里确实存在对应执行证据。

人工/外部验证配置 `type: manual` 或 `external`，通过 `ark evidence --help` 记录真实产物、
审查者和结果。通过 `policy.requirements` 将对应需求映射到必需检查；无需为了 ID 关联伪造测试。
自动化需求在实际测试源码中建立 REQ 引用，但文本关联不代表断言充分。

暂停/交接：

```bash
ark checkpoint --change bounded-output --summary 'Completed state and actual results' \
  --next 'Concrete next step' --blocked
ark context --session actual-session-id
```

不依赖聊天窗口续接；会话指针按仓库/worktree/分支/session 隔离，Checkpoint 跟随 Change。

## Hook、CI 与支持范围

| 接入点 | 0.1 实现 | 验证边界 |
| --- | --- | --- |
| Codex | AGENTS、Skills、SessionStart/Stop JSON 适配 | 协议子进程测试；实际加载/信任需目标环境确认 |
| Claude Code | CLAUDE 导入、Skills、SessionStart/Stop JSON 适配 | 保留已有设置；协议测试不能替代实际运行器验证 |
| OpenCode | 原生 Skills 与 AGENTS 入口 | 生命周期插件尚未实现 |
| 其他运行器 | 通用规则与仓内 CLI | 未宣称原生适配 |
| GitHub CI | 结构、真实差异范围、交付重跑、证据上传 | required checks/分支保护须独立配置 |

启动 Hook 只给少量上下文，不全仓扫描或跑业务测试。默认 advisory；将 `hook_mode` 设置
为 enforce 可在待交付证据不足时继续一次。它检查 `stop_hook_active` 和本地次数记录，
不会形成停止循环；明确 blocked 的任务允许交接。未配置会话指针时不猜测当前 Change。

`ark ci --base <real-base-ref>` 对真实源代码/配置差异检查范围，对相关活动或本次归档的 Change
重新执行验证；已有历史归档不会因新变更被全部重跑。它还检查 raw 证据和 Accepted ADR
正文的历史保护。仅规格阶段没有行为代码变化时可先通过结构阶段，不能据此关闭实现任务。

策略、运行内核、CI 和轻量声明都由仓库维护，须纳入代码审查；它们不是对恶意修改者的隔离边界。
详细支持状态和官方链接见 [兼容性说明](docs/compatibility.md)。

## 升级与开发

更新本机套件后显式执行 `ark init . --upgrade`。初始化记录管理文件摘要，人工修改会成为
可定位冲突。公共版本迁移、仓内定制和运行器信任分别处理，不在每次会话启动自动拉取最新版。

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m pip wheel --no-deps --no-build-isolation .
```

测试使用隔离临时仓库，覆盖初始化/重入、原规则保护、静态证据、基线锚点、实际消费者测试、
失败/缺失/超时/部分检查、手工证据、陈旧报告、归档、Hook 协议/有界继续、worktree 隔离与 CI。
构建产物包含 Skill、引用资料、模板、Schema 和消费仓 CI 资源。

进一步阅读：[架构与决策](docs/architecture.md) · [CLI](docs/cli.md) ·
[规格](openspec/specs/toolkit/spec.md) · [验证记录](docs/verification.md)
