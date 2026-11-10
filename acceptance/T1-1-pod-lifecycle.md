# T1-1 追一个 Pod 的一生（任务单）

> 用途：一份可复用的学习任务单。任务原文、当前进度、主干骨架、待答题、盲区都在这里，换会话或换机器都能接着走。下个任务复制本文件改名即可，见文末「复用方式」。
>
> 仓库内位置：`acceptance/T1-1-pod-lifecycle.md`；全局进度见 `progress.md`；考纲见 `plan/scheduler-roadmap.md`。

- 源码：kube-scheduler v1.32.0（`pkg/scheduler/**`，用 `scripts/setup-source.*` 拉取）
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

## 4. 粗颗粒验收记录（2026-11-09）

| # | 你的答案摘要 | 判定 | 依据 / 纠正 |
|---|---|---|---|
| A | 0 `Scheduler.Run` 收集待调度 Pod → 1 `NextPod` 逐个处理 → 2 `schedulePod` 选节点 → 3 `assume` → `bind` → 5 发给 apiserver/etcd | 🟡 模糊（2 处 🔴） | ① `Run` 不做收集：它只启动队列并起 goroutine 循环调 `ScheduleOne`（`scheduler.go:464`）；入队是 informer → `addPodToSchedulingQueue`（`eventhandlers.go:126`）→ `PriorityQueue.Add`（`scheduling_queue.go:598`）。② `NextPod` 只负责 `Pop`（`scheduler.go:378`、`scheduling_queue.go:857`）；处理逻辑在 `ScheduleOne`（`schedule_one.go:65`）。③ 阶段 3 不只 `assume`：还有 `RunReservePluginsReserve`（`framework.go:1370`）与 `RunPermitPlugins`（`framework.go:1454`）；`bind` 是阶段 4。④ 阶段 5 是 `finishBinding`（`:1000`）+ `RunPostBindPlugins`（`framework.go:1335`）；写 apiserver 在阶段 4。 |
| B | `assume` 时节点已定；`bind` 后集群可见；为了优化，`assume` 后可继续调度别的 Pod | 🟡 模糊（方向对） | 三个时间点要分开：**决定**节点是 `selectHost`（`:873`）；**调度器内部认为已定**是 `assume`（`:946`，写 `Pod.NodeName` + cache）；**集群可见**是 `Pods.Bind` 成功、apiserver 持久化之后。PVC 挂载更准确属于 PreBind / volume 相关，不是 bind 本身。 |
| C | 选节点只是映射，不代表绑定成功；写 apiserver 要和绑定完成对齐 | 🟡 模糊（前提对，机制错） | 写 apiserver **本身就是绑定**：写失败就是绑定失败，不存在「绑定失败却写了」。拆两个周期的真正原因：① 绑定是远程 I/O，同步做会阻塞调度循环；② `Permit` 可能返回 Wait（gang / 外部审批），不能占着主循环；③ `PreBind` 可能失败；④ `assume` 先记账，失败再回滚（`RunReservePluginsUnreserve` + `Cache.ForgetPod`）。这就是乐观并发：先占坑、后落地、失败退账。 |

### 复测（答完这 3 题，粗颗粒层才算过）

1. `Scheduler.Run` 到底做了什么？Pod 是在哪一步、由谁放进 activeQ 的？
2. 阶段 3 里 `assume` 之后还有哪两个调用？`Permit` 返回 Wait 时，绑定会立刻发生吗？
3. `Pods.Bind` 失败时，cache 里这个 Pod 的账还在吗？谁负责退？

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

> 继续 T1-1：读 `acceptance/T1-1-pod-lifecycle.md`，先答第 4 节的 A/B/C 三题。

完整验收记录：`acceptance/2026-11-07-scheduler-callchain.md`。

---

## 8. 复用方式（下个任务）

1. 复制本文件为 `T1-2-<任务名>.md` 等。
2. 只替换第 1 节（任务原文）和第 3 节（主干骨架）。
3. 清空第 2、4、6 节。
4. 第 5、7、8 节保留格式——它们是防止「回退到已澄清的错误」的锚点。
5. 出题前先写清「当前粒度」：粗颗粒只问阶段与职责；细颗粒才问函数、返回值、失败分支。
