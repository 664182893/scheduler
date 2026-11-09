# T1-1 追一个 Pod 的一生（任务单）

> 用途：一份可复用的学习任务单。任务原文、当前进度、主干骨架、待答题、盲区都在这里，换会话或换机器都能接着走。下个任务复制本文件改名即可，见文末「复用方式」。

- 源码：kube-scheduler v1.32.0（`pkg/scheduler/**`）
- 最近更新：2026-11-09
- 当前粒度：**粗颗粒（6 阶段）**，细节（cache / goroutine / 插件内部）暂缓

---

## 1. 任务原文

来源：《8 周学习 + 健身执行计划（源码攻坚版）》W1 必做卡 T1-1。

| 字段 | 原文 |
|---|---|
| 问题 | 从 informer 收到 Pod，到 bind 结果写回 apiserver，中间到底调了哪些函数？ |
| 动作 | 从 `scheduleOne` 开始，一个函数一个函数往下跟。每个函数记三样：**文件:行号**、一句话职责、它返回值被谁用了 |
| 交付 | 一张调用链图，至少 15 个节点，每节点带位置 |
| 验收 | **不看图，能口述完整链路** |
| 卡点 | 先只追主干（`schedulePod` → `findNodesThatFitPod` → `prioritizeNodes` → `assume` → `bind`），旁支全部跳过 |

---

## 2. 当前进度

- [x] 产出物形式核对：36 个节点、位置齐全、三要素齐全
- [x] 第 1 步编排（`schedule_one.go:65`）
- [x] 函数字段机制：`NextPod = podQueue.Pop`；`SchedulePod` / `FailureHandler` 是字段，不是方法
- [ ] **粗颗粒 6 阶段口述（当前卡在这里，见第 4 节）**
- [ ] 细颗粒 12 步（暂缓，主干通了再开）
- [ ] 终检：不看图口述完整链路

---

## 3. 粗颗粒主干（当前要掌握的）

记忆抓手：**入队 → 出队 → 选节点 → 占坑 → 绑定 → 收尾**。

| 阶段 | 从哪到哪 | 一句话职责 |
|---|---|---|
| 0 入队 | `eventhandlers.go:126` → `scheduling_queue.go:598 Add` | Informer 收到未绑定 Pod，放进 activeQ |
| 1 出队 | `scheduler.go:464 Run` → `schedule_one.go:65 ScheduleOne` → `NextPod/Pop:857` | 循环取下一个 Pod，选 Profile，跳过该跳的 |
| 2 选节点 | `schedulePod:411` → `findNodesThatFitPod:463` → `prioritizeNodes:755` → `selectHost:873` | 过滤出可行节点 → 打分 → 选最高 |
| 3 占坑 / 预留 | `assume:946` → `RunReservePluginsReserve:1370` → `RunPermitPlugins:1454` | 先在 cache 占坑，再跑插件级预留与放行 |
| 4 绑定 | `go func:121` → `bindingCycle:266` → `bind:968` → `DefaultBinder.Bind:51` | 异步把 Binding 写进 apiserver |
| 5 收尾 | `finishBinding:1000` → `RunPostBindPlugins:1335` | 确认绑定、清掉临时记账 |

这一层只要求说出阶段顺序和每段职责；`RunFilterPlugins` / `RunScorePlugins` / `WaitOnPermit` 等属于下一层。

---

## 4. 待答的 3 题（当前验收）

**A.** 按顺序说这 6 个阶段，每段用你自己的话说一句「它在解决什么问题」。不用背函数名，但要说出阶段之间的先后关系。

**B.** 哪一步之后「节点已经定了」？哪一步之后「集群里其他组件能看到这个 Pod 已绑定」？这两个时间点为什么不是同一个？

**C.** 为什么「选节点」和「写 apiserver」要拆成两个周期，而不是选完节点顺手就写？

---

## 5. 已澄清的事实（防回退）

1. `NextPod` 在 `scheduler.go:378` 被赋成 `podQueue.Pop`，是**阻塞出队**；入队是 `addPodToSchedulingQueue`（`eventhandlers.go:126`）→ `PriorityQueue.Add`（`scheduling_queue.go:598`），由 `Scheduler.Run`（`scheduler.go:464`）驱动循环。
2. `SchedulePod` / `FailureHandler` 是 `Scheduler` 的**函数类型字段**，在 `applyDefaultHandlers()`（`scheduler.go:114-115`）里分别绑定到 `schedulePod` / `handleSchedulingFailure`。调用处走的是字段，不是方法。
3. `handleBindingCycleError`（`schedule_one.go:129`）是异步失败兜底，不是主干；主干是 `bindingCycle` → `bind` → `RunBindPlugins` → `DefaultBinder.Bind`。
4. `NewCycleState`（`schedule_one.go:103`）只是本次调度周期的空状态容器，与 activeQ 无关；PreFilter 在 `findNodesThatFitPod` 里才跑。
5. `SchedulingQueue.Done`（`scheduling_queue.go:863`）只清理 in-flight 记账，不重入队也不出队。
6. 文档待修：`Pods.Bind @ default_binder.go:58` 标注不准确。该行是 `DefaultBinder.Bind` 内联调用 `ClientSet().CoreV1().Pods(ns).Bind(...)`，本仓库没有名为 `Pods.Bind` 的函数定义。

---

## 6. 盲区台账（摘要）

| 编号 | 盲区 | 状态 |
|---|---|---|
| G1 | 把 `NextPod` 当「入队」 | open |
| G2 | 选节点整段缺失（`ScheduleOne` 后直接跳到 `assume`） | open |
| G3 | 把 `handleBindingCycleError` 当主干 | open |
| G4 | 把 `NewCycleState` 当 PreFilter / 认为它让 Pod 进 activeQ | open |
| G5 | 不清楚 `SchedulingQueue.Done` 的语义 | open |
| G6 | 失败出口函数名说错 | open |
| G7 | 不理解 `FailureHandler` / `SchedulePod` 是函数字段 | fixed |

---

## 7. 恢复方式

新会话直接说：

> 继续 T1-1：读 `scheduler/acceptance/T1-1-pod-lifecycle.md`，先答第 4 节的 A/B/C 三题。

完整验收记录（本地，未推送）：`scheduler/acceptance/2026-11-07-scheduler-callchain.md`。

---

## 8. 复用方式（下个任务）

1. 复制本文件为 `T1-2-<任务名>.md` 等。
2. 只替换第 1 节（任务原文）和第 3 节（主干骨架）。
3. 清空第 2、4、6 节。
4. 第 5、7、8 节保留格式——它们是防止「回退到已澄清的错误」的锚点。
5. 出题前先写清「当前粒度」：粗颗粒只问阶段与职责；细颗粒才问函数、返回值、失败分支。
