# 验收记录：Kubernetes Scheduler 主干链路 + 失败回滚

- 日期：2026-11-07
- 验收方式：对话式逐轮提问（见 skill `dialogue-acceptance`）
- 验收对象：用户本人对链路的理解，而非文档本身的正确性

> **恢复入口（新会话直接说这句）**：
> “继续验收：读 `acceptance/2026-11-07-scheduler-callchain.md` 第 5 节的进度快照，先补答 C/D，再进第 2 步。”

## 0. 范围与版本

考纲来自《8 周学习 + 健身执行计划（源码攻坚版）》W1 必做卡 **T1-1 追一个 Pod 的一生**（`8周计划-源码攻坚版.html`，第 536–546 行），不是从产出物反推。

| 项 | 内容（任务卡原文） |
|---|---|
| 任务 | T1-1 追一个 Pod 的一生（90 min · 拆 3 次） |
| 问题 | 从 informer 收到 Pod，到 bind 结果写回 apiserver，中间到底调了哪些函数？ |
| 动作 | 从 `scheduleOne` 开始，一个函数一个函数往下跟。每个函数记三样：**文件:行号**、一句话职责、它返回值被谁用了 |
| 交付 | 一张调用链图，至少 15 个节点，每节点带位置 |
| 验收 | 不看图，能口述完整链路 |
| 卡点 | 先只追主干（`schedulePod` → `findNodesThatFitPod` → `prioritizeNodes` → `assume` → `bind`），旁支全部跳过 |
| 本次覆盖 | 仅 T1-1；T0-1（日志分段）、T0-2（FailedScheduling）、T1-2（goroutine 边界，弹性）不在本次 |
| 源码版本 | kube-scheduler v1.32.0（`pkg/scheduler/**`） |
| 产出物 | `SCHEDULER_CALLCHAIN.md`、`SCHEDULER_FAILURE_MATRIX.html` |
| 判分依据 | 代码实际行号（已逐条核对，不采信文档自述） |

### 产出物交付核对（只核对形式，不代表已通过）

| 要求 | 现状 | 结论 |
|---|---|---|
| 调用链图 ≥ 15 个节点 | 第 1 节 36 条、第 3 节 36 行，起点 `eventhandlers.go:126`，终点 `default_binder.go:58` | ✅ 数量达标 |
| 每节点带位置 | 36 个节点均有 `文件:行号` | ✅ |
| 每函数三样（位置 / 职责 / 返回值被谁用） | 第 3 节有「一句话职责」「返回值 → 消费者」两列 | ✅ |
| 覆盖范围 | 起点是 informer 回调，终点是 binding 写回，符合卡片边界 | ✅ |
| 事实准确性 | `Pods.Bind @ default_binder.go:58` 不准确：该行是 `DefaultBinder.Bind` 内联调用 `ClientSet().CoreV1().Pods(ns).Bind(...)`，本仓库没有名为 `Pods.Bind` 的函数定义 | ⚠️ 待修 |

> 本次验收只判「你能否口述」，不判文档文采。文档只是证据。

---

## 1. 验收方式调整

用户要求：按产出物第 6 节的「12 步跟读路线」逐步骤提问并引导学习，而不是一次性口述全链。

调整后：每步一个回合——先问该步的**自问** + 2 个三要素题；答完再进下一步。全部走完后，再回到卡片原验收标准「不看图口述完整链路」做终检。

### 第 1 步 · `schedule_one.go:65` 编排

| # | 问题 | 你的答案摘要 | 判定 | 依据 / 纠正 |
|---|---|---|---|---|
| 1-0 | （已答）从 Informer 收到 Pod 到写回，依次经过哪些函数？ | `ScheduleOne` → `NextPod` → `frameworkForPod` → `NewCycleState` → `assume` → `permit` → `handleBindingCycle` | 🔴 误解 + ⬜ 空白 | ① `NextPod` 是**出队**（`schedule_one.go:67` → `scheduling_queue.go:857 Pop`），不是入队；入队是 `eventhandlers.go:126 addPodToSchedulingQueue` → `scheduling_queue.go:598 Add`，由 `Scheduler.Run`（`scheduler.go:464`）驱动循环。② 漏 `skipPodSchedule`（`schedule_one.go:388`）。③ 从 `frameworkForPod` 直接跳到 `assume`，**整段选节点缺失**：`schedulingCycle:138` → `schedulePod:411` → `UpdateSnapshot:186` → `findNodesThatFitPod:463` → `RunPreFilterPlugins:709` / `findNodesThatPassFilters:591` → `prioritizeNodes:755` / `RunScorePlugins:1112` → `selectHost:873`。④ `handleBindingCycleError`（`:129`）是失败兜底，不是主干；主干是 `go func` → `bindingCycle:266` → `WaitOnPermit:1514` → `RunPreBindPlugins:1243` → `bind:968` → `RunBindPlugins:1286` → `DefaultBinder.Bind:51` → `Pods(ns).Bind`。 |
| 1-1 | `ScheduleOne` 从第 65 行到调用 `schedulingCycle` 之前，按顺序做了哪几件事？ | `NextPod`（自认为入队）→ `NewContext`（自认为 PreFilter）→ `frameworkForPod`（自认为选插件）→ profile 异常则「出队」→ skip 的 Pod 不重新入队 → CycleState「让 Pod 进入 activeQ」 | 🔴 误解 | ① `NextPod` 是 `PriorityQueue.Pop` 的别名（`scheduler.go:378` 赋值），**阻塞出队**。② `NewCycleState`（`:103`）只是建空状态容器，与 PreFilter 无关；PreFilter 在 `findNodesThatFitPod` 里才跑（`framework.go:709`）。③ `frameworkForPod`（`:379`）按 `schedulerName` 选 **Profile**（一套插件配置），不是「选插件」。④ profile 异常 / skip 调的是 `SchedulingQueue.Done`（`:90`、`:95`；实现 `scheduling_queue.go:863`），只清理 in-flight 记账，**既不是入队也不是出队**。⑤ `CycleState` 与 `activeQ` 无关；Pod 在 `Pop` 时就已离开 activeQ。 |
| 1-2 | 第 120 行的 `go func` 为什么必须放在 `schedulingCycle` 成功之后？ | 「是不是会发生资源超配？」 | 🟡 模糊 | 方向对（超配是后果），但缺根因：`bindingCycle` 的入参 `assumedPodInfo` 是 `schedulingCycle` 的返回值；`assume` 已写入 `assumedPods` 与节点账本，Reserve 可能占了插件资源、Permit 可能 Wait。这三件事未完成就开子 goroutine，主循环会去取下一个 Pod，账本没记 → 真会超配。代码注释 `:119` 已点明：`we can do this b/c of the assumption step above`。 |
| 1-3 | 第 114 行和第 128 行两个失败出口，分别调谁？各在哪个 goroutine 上？ | 114 调「里面 SchedulePod 那个函数」，主 goroutine；128 调 `bindingCycle`，不确定哪个 routine | 🔴 误解 | ① `:115` 调 `sched.FailureHandler` = `handleSchedulingFailure`（绑定于 `scheduler.go:115`），主 goroutine，同步。② `:129` 调 `sched.handleBindingCycleError`（`:345`），在 `:120` 的 `go func` 内，**子 goroutine**。③ `:127` 才是调 `bindingCycle`；`:128` 只是判它的 status。④ `SchedulePod` 是 `schedulingCycle` 内部（`:149`）调的，不是 114 行调的。 |

#### 第 1 步复测记录

| 题 | 你的回答 | 判定 | 说明 |
|---|---|---|---|
| A. `sched.NextPod` 真正执行谁？ | `podQueue.Pop`，`scheduler.go:378` | ✅ 掌握 | 函数字段机制已说对 |
| B. 替换 `sched.SchedulePod` 后还会走真选节点吗？ | 不会，注册函数被改了 | ✅ 掌握 | 精确表述：`schedulingCycle:149` 调的是字段，字段已指向匿名函数，`schedulePod:411` 及其下所有选节点逻辑不会执行 |
| C. `:116` / `:130` 各在哪个 goroutine？cache 状态一样吗？ | 暂缓 | ⏸ 暂缓 | 细节题，按「先粗后细」规则移到第 11 步（assume）再考 |
| D. 去掉 `:121` 的 `go` 会怎样？ | 暂缓 | ⏸ 暂缓 | 细节题，移到第 12 步（bind 与异步）再考 |

### 粗颗粒主干（2026-11-09 起）。先只要求能按阶段口述，不考 cache 内部。

| 阶段 | 入到出 | 一句话职责 | 你的自述 |
|---|---|---|---|
| 0 入队 | `eventhandlers.go:126` → `scheduling_queue.go:598 Add` | Informer 收到未绑定 Pod，放进 activeQ | 待答 |
| 1 出队 | `scheduler.go:464 Run` → `schedule_one.go:65` → `NextPod/Pop:857` | 循环取下一个 Pod，选 Profile，跳过该跳的 | 待答 |
| 2 选节点 | `schedule_one.go:411` → `463` → `755` → `873` | 过滤出可行节点 → 打分 → 选最高 | 待答 |
| 3 记账 / 预留 | `946 assume` → `framework.go:1370 Reserve` → `1454 Permit` | 先占坑，再跑插件级预留与放行 | 待答 |
| 4 绑定 | `schedule_one.go:121 go func` → `266` → `968 bind` → `default_binder.go:51` | 异步把 Binding 写进 apiserver | 待答 |
| 5 收尾 | `1000 finishBinding` → `framework.go:1335 PostBind` | 确认绑定、清 assumed 状态 | 待答 |

> 这 6 阶段就是任务卡里「主干」的粗粒度版本；`findNodesThatFitPod` / `RunFilterPlugins` / `RunScorePlugins` / `WaitOnPermit` 等属于下一层细节，本阶段只需要能说出它们属于哪一段。

### 后续步骤（待逐轮填写）

| 步 | 跳转 | 该步自问 | 状态 |
|---|---|---|---|
| 2 | `schedule_one.go:138` | 失败后谁负责回滚？ | 待答 |
| 3 | `schedule_one.go:411` | 只有一个可行节点时为什么直接返回？ | 待答 |
| 4 | `schedule_one.go:463` | PreFilter 的 STATUS 有几种流向？ | 待答 |
| 5 | `framework.go:709` | PreFilterResult 如何缩小节点集？ | 待答 |
| 6 | `schedule_one.go:591` | 为什么要「找到一个就 cancel」？ | 待答 |
| 7 | `framework.go:984` | 提名 Pod 为什么要跑两轮 Filter？ | 待答 |
| 8 | `schedule_one.go:755` | TotalScore 怎么累加？ | 待答 |
| 9 | `framework.go:1112` | 为什么按插件并发而不是按节点？ | 待答 |
| 10 | `schedule_one.go:873` | 为什么不直接取 max？ | 待答 |
| 11 | `schedule_one.go:946` + `cache.go:361` | 为什么 bind 还没成功就记账？ | 待答 |
| 12 | `schedule_one.go:968` → `default_binder.go:51` | 失败时谁清理 assumed 状态？ | 待答 |

---

## 2. 盲区台账

| 编号 | 现象 | 正确表述 | 依据 | 复现次数 | 状态 |
|---|---|---|---|---|---|
| G1 | 把 `NextPod` 当「入队」 | `NextPod` 是出队；入队是 `addPodToSchedulingQueue` → `PriorityQueue.Add` | `schedule_one.go:67`、`scheduling_queue.go:857`、`eventhandlers.go:126`、`scheduling_queue.go:598` | 2 | open |
| G2 | 选节点整段缺失（`ScheduleOne` 后直接跳到 `assume`） | 必须先经 `schedulePod` → `findNodesThatFitPod` → `prioritizeNodes` → `selectHost` 才能得到 host | `schedule_one.go:411/463/755/873` | 1 | open |
| G3 | 把 `handleBindingCycleError` 当主干 | 它是异步失败兜底；主干是 `bindingCycle` → `bind` → `RunBindPlugins` → `DefaultBinder.Bind` | `schedule_one.go:129` vs `:266/968` | 1 | open |
| G4 | 把 `NewCycleState` 当 PreFilter / 认为它让 Pod 进 activeQ | CycleState 只是本次调度周期的空状态容器，与队列无关 | `schedule_one.go:103` | 1 | open |
| G5 | 不清楚 `SchedulingQueue.Done` 的语义 | 只清理 in-flight 记账（QueueingHint 开启时），不重入队也不出队 | `scheduling_queue.go:863` | 1 | open |
| G6 | 失败出口函数名说错 | `:115 FailureHandler`；`:129 handleBindingCycleError` | `schedule_one.go:115/129` | 1 | open |
| G7 | 不理解 `FailureHandler` / `SchedulePod` 是函数字段 | `Scheduler` 上有函数类型字段，启动时 `applyDefaultHandlers()` 把 `SchedulePod` 指向 `schedulePod`、`FailureHandler` 指向 `handleSchedulingFailure`（`scheduler.go:114-115`），目的是方便测试替换 | `scheduler.go:114-115` | 1 | fixed（第 1 步复测 A/B 已答对） |

---

## 3. 结论

待验收结束填写：通过 / 有条件通过 / 重做。

## 4. 复读清单

待验收结束填写。

---

## 5. 进度快照（2026-11-07 暂停，2026-11-09 继续）

| 项 | 状态 |
|---|---|
| 粒度 | 自 2026-11-09 起改为**先粗后细**：先按「6 阶段主干」验收，cache / goroutine 细节暂缓 |
| 第 1 步 `schedule_one.go:65` | ✅ 收口（C/D 降级为暂缓，不判失败） |
| 粗颗粒主干 | 🔄 进行中：6 阶段表待用户逐阶段口述 |
| 第 2–12 步 | ⏳ 细颗粒阶段再开，顺序不变 |
| 盲区 | G1–G6 open，G7 fixed |
| 下次入口 | 用户逐阶段用自己的话讲 6 阶段主干（不考 cache 内部） |
