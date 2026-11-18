# 源码事实审查

审查日期：2026-11-18。审查者：Codex（本次独立子任务；本报告内两轮为同一审查者的分离审查，不声称两位审查者独立复核）。

## 结论与状态

**PENDING：发现 2 处规范与实现的直接矛盾、4 处断言或证据范围问题，另记录 1 项行为覆盖限制。** 原生测试 5/5 通过，不能证明这 3 条需求得到验证。REQ-HUB-003 的无条件返回值描述符合源码，但映射将它错误地缩窄为 `token == 0`，且没有接收器测试。

本次只审查并记录问题，不修改 `spec.md`、`review-mapping.json`、业务源码、头文件、Makefile 或测试，也不将已发现差异改写为已接受行为。所有发现保持 open，供后续决定修正规范还是实现。

## 实际范围与方法

- 业务文件范围严格限于本目录：`hub.c`（132 行）、`hub.h`（32 行）、`main.c`（29 行）、`Makefile`（17 行）、`tests/test_hub.py`（44 行）。完整阅读这些文件，再阅读全部 `spec.md`（27 行）和 `review-mapping.json`（31 行）；没有在其他项目搜索业务实现。
- 流程参考仅从指定 `agent-repo-kit/skills/baseline-repo/SKILL.md` 及其 `references/source-facts.md`、`behavior-model.md`、`source-audit.md` 读取。先按代码入口、分支及副作用建立下表，再逐条对照文档与实际断言。
- 构建同时将同一个 `hub.c` 编入 CLI 与共享库（`Makefile:L5-L14`）；头文件对外暴露 16 个函数。CLI 只直接暴露初始化、serve、resources、dispatch，其余接口通过共享库被调用，不把没有 CLI 分支误作没有可调用行为。
- 原始目录只有上述 7 个输入文件。未发现本目录的其他构建配置、启动脚本或实现；不推断外部调用方、外部产品承诺、Git 修订或项目整体已完成初始化。
- 首轮完成源到文档、文档到源及断言审查，先记录发现；之后第二轮重新完整打开相同 7 个输入，重建分支与调用检查，结果单独记录于下方。
- 本任务明确限于审查，不执行初始化、登记、生成行为清单或其他工程资产，也不修改原始输入。

## 从源码重建的事实与覆盖分母

以下事实包含文档没有描述的可观察行为；“未覆盖”是证据边界，不表示每个实现细节都应提升为 SHALL。

| 行为 | 生效路径、条件及实际结果 | 检查的反例／边界 | 文档与测试覆盖 |
| --- | --- | --- | --- |
| B01 初始化与信号 | `hub_initialize` 先为 SIGTERM 安装 `shutdown_handler`，随后 `install_common_handlers` 覆盖 SIGTERM 并安装 SIGABRT。最终 handler 恢复默认动作并重新发送信号；初始化无条件返回 0，未检查 `signal` 结果（`hub.c:L18-L39`）。 | `serve` 输出 ready 后发 SIGTERM；实际按信号终止，无 flushed。不能从先前定义的 shutdown handler 推导清理或正常退出。SIGABRT 同一路径仅静态核对。 | 无条款。`test_initialize` 只断言返回 0，不能证明信号、副作用或资源列表。 |
| B02 资源集合 | 有效静态表仅 `stream`、`probe`，count 为 2；越界索引返回 NULL。初始化不改表。CLI 依 count 顺序输出（`hub.c:L9,L35-L47`，`main.c:L18-L23`）。`RESOURCE_ARCHIVE` 仅为未使用宏（`hub.h:L7`）。 | CLI resources、索引 0/1/2/100；第 3 项不存在。 | REQ-HUB-001 错误；映射的初始化断言不观察资源。 |
| B03 命令分派 | 精确匹配 `deploy/remove/inspect`，返回 0/1/2，未知字符串返回 -1（`hub.c:L10,L49-L56`）。CLI 将返回值打印，命中 dispatch 形式后进程仍返回 0（`main.c:L24-L27`）。 | remove、inspect、archive、Deploy；未知命令为输出 -1、进程退出 0。不传 NULL 给 `strcmp`；源码没有 NULL 保护。 | 无条款或映射；`test_deploy_command` 只检查 deploy 的 `0\n`（`tests/test_hub.py:L25-L30`）。 |
| B04 身份 | `hub_identity()` 固定返回 `hub.v2`（`hub.c:L58-L60`）。 | 调用后观察该字面值；未据此推导协议版本兼容承诺。 | 无条款、映射或测试。 |
| B05 编码 | `hub_encode(value)` 构造 `{0, value}`；token 固定 0，value 原样返回（`hub.c:L62-L65`）。 | value 为 C int 最小值、0、42、最大值。没有计算或检查完整性字段。 | 无编码条款；`test_frame_value` 只观察 encode(42).value（`tests/test_hub.py:L32-L33`），不检查 token、不调用 receive。 |
| B06 接收 | `hub_receive(Frame)` 无条件 `return frame.value`，不读 token（`hub.c:L67-L69`）；Frame 为 uint32_t token 加 int value（`hub.h:L10-L13`）。 | token=0/1/UINT32_MAX 与 int 最小值/0/42/最大值的组合均原样返回 value。 | REQ-HUB-003 本身与源码一致；映射的 token==0 条件不足以承接无条件条款，tests 为空。 |
| B07 周期 | 变量初值 10；`hub_period_valid(s)` 是独立的 1≤s≤600 谓词；`hub_update_period(s)` 不调用它，只对 s≤0 返回 -1，否则写 period=s 并返回 s（`hub.c:L12,L71-L81`）。此快照没有 period getter 或实际调度消费者。 | -1/0 拒绝，1/600 接受；601/700/INT_MAX 也接受。写入 700 是赋值语句的静态事实，运行返回值本身不是独立存储读回。 | REQ-HUB-002 错误；映射只引用未被调用的校验函数及合法值 12 的断言。 |
| B08 过滤器 | 数组分配 6 槽，但有效上界为 `FILTER_SLOTS - 2`，即 count≤4。超出返回 -2；0 无操作返回 0；1..4 对前 count 槽先 free 再 strdup("configured")，返回 0（`hub.h:L8`，`hub.c:L11,L83-L92`）。缩小时不清除较高槽位；未检查 strdup 失败。 | 0/2/4 返回 0，5/6/7/SIZE_MAX 返回 -2；分配失败及内部槽位内容仅静态核对，未做故障注入。不能以 6 槽推导“支持 6 项”。 | 无条款或映射；`test_filter_configuration` 调用 count=2 后只断言另一个函数 initialize()==0（`tests/test_hub.py:L38-L40`），没有检查过滤器返回值或状态。 |
| B09 路由优先级 | global_enabled 非零优先返回 global；否则 local_enabled 非零返回 local；两者均零返回 disabled（`hub.c:L94-L102`）。 | (0,0)/(0,1)/(1,0)/(1,1)/(0,-1)/(-1,2)，包括双方启用及非 1 真值。 | 无条款、映射或测试。 |
| B10 窗口复位及查询 | reset(now) 设置 watermark=now、累计=0、reports=0、last_fields=-1；两个 getter 读取计数与上次字段数（`hub.c:L104-L109,L122-L128`）。这些 static 变量在 reset 前由 C 零初始化，last_fields 初始为 0，不能无条件声称 -1。 | reset 后查询得到 0/-1；未将 reset 后状态等同启动状态。 | 无条款、映射或测试。 |
| B11 窗口推进及事件归属 | 仅 ingest 计算 `now-watermark > 20`；严格超过时先 reports++、记录旧累计、watermark=now、累计归零，再累计本条 fields。value 被忽略。一次 ingest 最多报告一次，旧累计为空也可报告（`hub.c:L111-L120`）。源码未声明 now 的时钟或单位。 | reset(0)，ingest(0,fields=3)、ingest(20,4) 均不报告；ingest(21,5) 报告旧累计 7；后续 ingest(42,6) 报告 5；大跳跃到 200 只增加一次；空窗口直接在 21 ingest 报告 0。 | 无条款、映射或测试。不能推导固定周期调度、“≥20”、触发记录计入旧窗口或跳跃补齐所有窗口。 |
| B12 tick | `hub_window_tick(now)` 忽略 now，不改任何状态（`hub.c:L130-L132`）；本目录无定时器注册或后台线程。 | 上述在 21 ingest 后 tick(100) 仍 reports=1、last_fields=7。 | 无条款、映射或测试；时间推进没有新 ingest 时不产生报告。 |
| B13 CLI 与装配 | main 先初始化；无参数退出 1；serve 输出 ready 并 pause 循环；resources 列表后退出 0；dispatch 且 argc==3 时打印结果并退出 0；其余退出 2（`main.c:L7-L29`）。Makefile 以 C99、警告作错误构建 CLI 和 .so，test 调用 unittest discover（`Makefile:L1-L17`）。 | 无参数、未知主命令、dispatch 缺参／多参、已知／未知子命令；serve 的 SIGTERM 单独子进程探测。未执行无信号的无限等待。 | 无 CLI／生命周期条款；仅 deploy 具有实际 CLI 断言。 |

## 逐条条款、场景与断言结果

| 需求与条款位置 | 条款／场景事实 | 声明映射实际能证明什么 | 审查状态 |
| --- | --- | --- | --- |
| REQ-HUB-001，`spec.md:L8-L13` | SHALL 和场景都要求 3 个资源；当前可观察集合是 2 个，不含 archive。 | `review-mapping.json:L2-L10` 罗列头文件和源码，条件为初始化后；`test_initialize` 只调用 initialize 并比较 0，不读 count、不枚举名字、不调用 resources CLI。初始化后也没有 archive。 | 条款／场景矛盾；自动化证据缺失。 |
| REQ-HUB-002，`spec.md:L15-L20` | 对 >600 的拒绝保证不成立；700 实际返回 700，并执行 period=700。≤0 拒绝只是区间外的一个子集。 | `review-mapping.json:L12-L19` 的 `hub_period_valid` 只有定义，没有 update 路径的调用；`test_period_configuration` 只验证 12→12，不刺激上下界或 700，亦不读回拒绝后的存储。 | 条款／场景矛盾；错误证据路径；边界及不写入断言缺失。 |
| REQ-HUB-003，`spec.md:L22-L27` | 任意可表示 Frame 按值传入时，value 无条件返回；不存在 token==0 前提。场景也未限定 token。 | `review-mapping.json:L21-L29` 的源码符号正确，但条件仅 token==0，tests=[]；将非零 token 标为“未提升观察”与已写出的无条件 SHALL 不一致。现有 encode 测试不能替代 receive 测试。 | 源码支持条款；映射范围及执行证据 PENDING。 |

## 首轮发现（先记录、未修订输入）

| ID／级别／状态 | 具体问题及位置 | 实际事实、反证与影响 | 后续处置依据 |
| --- | --- | --- | --- |
| SR-001／高／open | 资源集合与数量写错：`spec.md:L10,L13`。 | `hub.c:L9,L41-L47` 只有 stream/probe；`main.c:L18-L23` 实际输出这两行。`hub.h:L7` 的 archive 宏没有进入有效表或任何调用。资源发现客户端据规范期待 archive 将失败。 | 必须明确修正规范还是变更实现；仅添加来源文件名或引用宏不能消除矛盾。 |
| SR-002／高／open | 周期上界与禁止写入承诺不成立：`spec.md:L17-L20`。 | `hub.c:L75-L80` 的反例 700 命中 `period=seconds`，返回 700；601、INT_MAX 同理。有效更新路径完全不调用 `hub_period_valid`。规范宣称的拒绝及状态保持均失效。 | 必须处理实现／承诺冲突；不能用未调用的 validator 为当前更新接口背书。 |
| SR-003／中／open | 资源“自动化验证”映射了不观察资源的断言：`review-mapping.json:L9-L10`、`tests/test_hub.py:L22-L23`。 | 即使资源为空、缺 archive 或顺序／名称错误，只要 initialize 返回 0，该断言仍通过；实际 native suite 通过而 SR-001 存在就是具体反例。文件级 sources 不补足执行观察。 | 应使用调用有效资源路径、断言全部名称／数量及适当边界的证据；本次不增改测试，仍为验证缺口。 |
| SR-004／中／open | 周期来源与测试无法支撑区间拒绝：`review-mapping.json:L15,L18-L19`、`tests/test_hub.py:L35-L36`。 | 谓词 700→0，与 updater 700→700 可同时成立；合法 12→12 的断言对“接受 700”的错误不会失败。没有 ≤0、1、600、601/700 的更新路径断言，也无拒绝后状态断言。 | 映射应跟踪实际 updater 的条件、赋值、返回和调用关系；分开记录边界拒绝与不写入的观测限制。 |
| SR-005／中／open | 证据条件被缩窄，遗漏已承诺域：`review-mapping.json:L26-L29` 对照 `spec.md:L24-L27`。 | `hub_receive` 不检查 token；token=1,value=42 仍返回 42。当前无条件 SHALL 已包含非零 token，不能把它说成“未提升观察”。即使 token==0 的子域已验证，也不能关闭整条需求。 | 应统一完整输入域或显式处理真实承诺变更；现有条款本身有源码支持，不应为了映射方便悄悄改窄。 |
| SR-006／中／open | 接收需求声明 automated 却没有任何接收断言：`spec.md:L23`、`review-mapping.json:L28`、`tests/test_hub.py:L18-L20,L32-L33`。 | tests=[]；现有测试只绑定并检查 encode(42).value，没有调用或观察 hub_receive。若 receive 恒返回 0，原测试仍会通过。正确源码分析不能冒充已执行的回归验证。 | 保留自动化方法意图并列为未验证，直到真实 receive 刺激／断言覆盖 value 与完整 token 条件；临时探测不自动成为受维护的测试映射。 |
| SR-007／范围限制／open | 两份文档只记录 3 条需求，没有覆盖其余有效接口，也没有完整行为清单：`spec.md:L3-L4,L6-L27`、整个 `review-mapping.json`。这限制整体覆盖结论，不单独构成已有 SHALL 的错误。 | 从有效构建与全部 API 重建的 B01、B03-B05、B08-B13 未进入这些文件；包括最终信号处理覆盖、3 个命令及未知路径、身份字面值、token 编码、count≤4、global 优先、严格惰性窗口及空 tick。这些都具有真实分支或外部结果。当前测试对其中多数也不观察。 | 如需声称完整运行接口覆盖，应先明确选定条款范围和剩余行为；是否提升为规范需逐项判断，不自动把实现细节／潜在缺陷写成 SHALL。本报告已保留未覆盖分母，不将 3 条需求等同全项目规范覆盖。 |

## 真实执行与观察

1. 在本目录执行 `make test`，退出码 0。实际命令为：

   ```text
   cc -std=c99 -Wall -Wextra -Werror -O0 -g hub.c main.c -o build/hub
   cc -std=c99 -Wall -Wextra -Werror -O0 -g -shared -fPIC hub.c -o build/libhub.so
   python3 -m unittest discover -s tests -v
   ```

   5 个测试全部执行并通过：test_deploy_command、test_filter_configuration、test_frame_value、test_initialize、test_period_configuration。没有跳过、失败或超时。原命令未传入整套测试超时参数；工具在 10 秒首个等待窗口内即返回，构建和测试共约 0.19 秒，unittest 自报 0.002 秒。此结果只说明这 5 个实际断言通过，尤其不是 3 条需求均验证通过。执行环境为 cc (Debian 14.2.0-19) 14.2.0、Python 3.12.14。

2. 使用一次性 `python3` 脚本，以显式 ctypes argtypes/restype 调用新构建的共享库，并以 `subprocess` 调用 CLI；脚本未写入测试文件。CLI 子进程和 serve 就绪／终止等待均设置 3 秒超时，全部完成。输出观察如下（它们是审查探测，非现有测试套件新增用例）：

   | 探测 | 实际观察 |
   | --- | --- |
   | resources CLI | 退出 0，stdout=`stream\nprobe\n`；count=2；索引 2/100 为 NULL。 |
   | `(seconds, valid, update)` | `(-1,0,-1)`、`(0,0,-1)`、`(1,1,1)`、`(600,1,600)`、`(601,0,601)`、`(700,0,700)`、`(2147483647,0,2147483647)`。 |
   | identity | `hub.v2`。 |
   | encode | 对 -2147483648/0/42/2147483647：token=0，value 保持。 |
   | receive | token 0/1/4294967295 × value -2147483648/0/42/2147483647，共 12 组，全部返回 value。 |
   | configure_filters | count=0/2/4 返回 0；5/6/7/18446744073709551615 返回 -2（本环境的 64 位 size_t）。只观察返回值，未读内部槽位。 |
   | route | (0,0)→disabled；(0,1)/(0,-1)→local；(1,0)/(1,1)/(-1,2)→global。 |
   | CLI 形式 | 无参数退出 1；unknown、dispatch 缺参／多参退出 2；dispatch deploy/remove/inspect 输出 0/1/2；dispatch archive/Deploy 输出 -1，但这些 dispatch 进程均退出 0。 |
   | 窗口 | reset(0) 后 reports=0,last=-1；在 now=0/20 加 3/4 不报告；在 21 加 5 后 reports=1,last=7；tick(100) 不变；42 加 6 后 reports=2,last=5；200 加 9 后 reports=3,last=6。另一次 reset(0) 后首次在 21 加 5，reports=1,last=0。 |
   | serve + SIGTERM | 就绪输出 `ready\n`；发送 SIGTERM 后 returncode=-15，之后 stdout/stderr 均空，没有 `flushed`。 |

3. 不做业务源码变异、不修改测试或规范，不以此套件通过掩盖发现。SIGABRT、信号安装失败、分配失败、内存泄漏、并发、C int 算术溢出及所有整数值的穷举没有动态验证；对应语句虽已静态阅读，不声称运行安全或完整容错。没有外部系统集成测试，也没有断言私有 period 的独立读回。

## 第二轮重开源码复核

首轮报告写入后，重新打开完整的 `hub.c:L1-L132`、`hub.h:L1-L32`、`main.c:L1-L29`、`Makefile:L1-L17`、`tests/test_hub.py:L1-L44`，以及完整 `spec.md:L1-L27`、`review-mapping.json:L1-L31`。另在本目录重新检索宏、校验器、更新函数、接收函数、token、信号设置、过滤器状态及 tick，确认没有隐藏的表追加、调用校验或 token 检查。此轮是同一审查者的分离源码重读，不是哈希／格式校验替代语义复核；不声称独立审查者，也不声称修复后复核，因为没有修复输入。

| 首轮 ID | 第二轮实际复核路径与结果 | 最终状态 |
| --- | --- | --- |
| SR-001 | 头文件宏 → `hub.c:L9,L35-L47` 的实际表及不改表的初始化 → `main.c:L18-L23` 的 count 驱动输出。没有第三项、没有后续注册或覆盖。 | open，矛盾仍成立。 |
| SR-002 | `hub_period_valid:L71-L73` 与 `hub_update_period:L75-L81` 的调用关系重新检查；唯一调用 updater 的现有测试输入仍为 12。700 仍直接赋值，<=0 才拒绝。 | open，矛盾仍成立。 |
| SR-003 | 重读 initialize 的全部副作用和 `test_initialize:L22-L23`；断言只有返回码，没有资源访问。 | open，断言观察不相关。 |
| SR-004 | 重读 updater 的拒绝、赋值、返回相邻路径，核对 mapping.sources 和实际合法值断言；没有独立状态查询入口。 | open，区间及状态保持验证缺失。 |
| SR-005 | Frame 定义 → encode 固定 token → receive 无条件返回 value；重新对照无条件 SHALL、场景与 token==0 限定及非零“未提升”文本。 | open，映射域仍小于承诺域。 |
| SR-006 | 完整重读测试绑定及所有测试体，确认只有 encode 接口被检查，没有 receive 调用；mapping 的 tests 仍为空。 | open，自动化未完成。 |
| SR-007 | 从 16 个公开函数、CLI 全部分支及 Makefile 两个产物重建 B01-B13，对照文档全部 3 条需求；再读信号最终覆盖、count 的 4 项上界、双真路由、严格 >20、先报告后累计、空 tick 等相邻路径。 | open，作为范围限制保留；未把遗漏自动认定为每项都必须新增承诺。 |

第二轮没有新增源与条款矛盾；以上全部问题未经修复，不能据此报告“零问题”或 verified-completion。临时探测的实测事实、静态证明和受维护断言继续分开记录。

### 与本次范围相符的质量结论

- 规格自足性：PENDING。除了前述错误和范围矛盾，周期场景只写“error”，没有约定错误返回值；“不存储”也没有给出可观测检查方法，本快照没有独立 period 读回接口。接收场景没有 token 前提，不能从映射暗补该前提以缩窄承诺。不得用源码细节暗补规范以声称场景已完整验证。
- 能力覆盖：有限范围已静态检查 B01-B13，3 条规范仅涉及 B02、B06、B07；未覆盖行为列在 SR-007。这不是整个上层仓库、设备系统或历史 onboarding 的覆盖声明。
- 项目入口、工程登记与初始化：按本次明确任务排除，没有生成或审查其他 AGENTS、registry、OpenSpec 配置、历史产物或项目初始化资产；不据此得出它们合格的结论。

## 原始输入指纹

以下为首轮开始前 SHA-256；最终保存后再次核对，7 项均与这些指纹相同。原生检查产生的 `build/` 和 `tests/__pycache__/` 均为本次临时产物，检查后移除；只新增本报告及按补充指令保存的 `task.txt`：

| 文件 | SHA-256 |
| --- | --- |
| spec.md | `7f45c2617131edca73aea6486a8f0c81bae44ccedb3ffeff20f56e6cc666b3cc` |
| review-mapping.json | `840caa761cfb514277fe77eca1b0e768a37b73477dd7f1dceefa2e99179f080d` |
| hub.c | `fca1a7e61e47b52eff97391a6f9c5aeb3f11d21ab73eac6b9027f6df11154bd8` |
| hub.h | `c91220bd81440a84e88b83cf86d02bafd56a00c09295d038ace2311c5054f226` |
| main.c | `773c08be88c4523f9c6725b01c6b22cf618061060983856e585c9622f3955905` |
| Makefile | `79407234c150d0a721539b8866269f3ba4e6c8009d179ce18b81ab9cc94b6ebd` |
| tests/test_hub.py | `2347b3f6d5c11100409db973befb8d61279f3b9ab778afbba28eebe1cd5c0a0d` |
