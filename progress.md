# 进度总表

- 最近更新：2026-11-22
- 当前任务：**T1-1 追一个 Pod 的一生**
- 当前粒度：**细颗粒 12 步 · 第 3 步（`schedulePod`）已通过；下一步第 4 步（`findNodesThatFitPod`）**
- 源码版本：kube-scheduler v1.32.0
- 每日执行：见 `plan/daily-plan.md`
- 源码位置：各机器用 `scripts/setup-source.*` 拉取；本仓库不提交源码
- 注释汉化：2026-11-22 已完成调度器非测试源码 124 个文件（`pkg/scheduler/**`、`cmd/kube-scheduler/**`、`staging/k8s.io/kube-scheduler/**`，排除 `*_test.go`）的中文注释；映射在 `scripts/annotations/`，一键恢复用 `scripts/apply-annotations.*`
- 主干文档：`docs/T1-1-pod-lifecycle-6stages.md`（带行号超链接）
- 回顾总纲：`docs/SCHEDULER_STUDY_GUIDE.md`（汇编版，含机制、失败矩阵、自测、行号速查）
- 当日复盘：`docs/review-2026-11-18.md`（11-15 的见 `docs/review-2026-11-15.md`）
- 练习：`docs/worksheet-T1-1-flowchart.md`（流程图填空）

## 下次入口

1. 粗颗粒层与细颗粒第 2、3 步已通过（G13–G17 关闭）。
2. 下一步：第 4 步 `findNodesThatFitPod`（`schedule_one.go:463`）——PreFilter / Filter / Diagnosis 的编排。
3. G1（cache/queue 混用）仍为 must-fix，持续观察。

## 细颗粒第 2 步记录（2026-11-13）

对象：`schedulingCycle`（[`schedule_one.go:138-263`](https://github.com/kubernetes/kubernetes/blob/v1.32.0/pkg/scheduler/schedule_one.go#L138)）

### 本轮问答与判定

| 题 | 你的答案 | 判定 | 纠正 |
|---|---|---|---|
| 返回值消费方 | 返回值给 `ScheduleOne`；第二个是副本 | 🟡 | 副本的必要性未答。原因：`assume` 会改写 `Spec.NodeName`，污染队列版本 |
| `SchedulePod` 失败 | 没有退账 | ✅ | 正确，`assume` 尚未执行 |
| `assume` 失败 | 有清理缓存 | 🔴 | **错**：`AssumePod` 已失败，账未记事，再 `ForgetPod` 会报 `wasn't assumed` |
| `Reserve` 失败 | 有退账 | 🟡 | 缺具体两个动作：`RunReservePluginsUnreserve` + `Cache.ForgetPod` |
| `Permit` 失败 | 没有退账 | 🔴 | **说反了**：`:234-237` 明确退账（与 `assume` 弄反） |
| `Wait` 为何排除 | Wait 当失败会退账，gang 凑不齐 | ✅ | 机制描述准确 |

### 四条出口速查

| # | 出口 | 退账 | Status |
|---|---|---|---|
| 1 | `ErrNoNodesAvailable` | 无 | `UnschedulableAndUnresolvable` |
| 2 | FitError → PostFilter | 无 | `Unschedulable` |
| 3 | `assume` 失败 | **无** | `Error` |
| 4 | `Reserve` 失败 | `Unreserve` + `ForgetPod` | `Reject` → `FitError` |
| 5 | `Permit` 失败 | `Unreserve` + `ForgetPod` | `Reject` → `FitError` |

**口诀：账记上了才要退。**

### 待答复测题

1. `assume` 失败时为什么不调 `ForgetPod`？硬要调会撞上哪一行、报什么错？
2. `Reserve` 失败与 `Permit` 失败的退账动作完全相同吗？说出两个函数名。
3. 为什么需要 `podInfo.DeepCopy()`？直接改写原对象，失败重入队时会怎样？

### 复测结果（2026-11-15）

| # | 判定 | 要点 |
|---|---|---|
| 1 | ✅ | `assume` 失败不调 `ForgetPod`；硬调会命中 `cache.go:422` 的 `wasn't assumed so cannot be forgotten` |
| 2 | ✅ | `Reserve` / `Permit` 失败都是 `RunReservePluginsUnreserve` + `Cache.ForgetPod`；`Unreserve` 逆序（`framework.go:1427`） |
| 3 | ✅ | `DeepCopy` 防止 `assume` 写 `NodeName` 污染 informer；不复制会让 `handleSchedulingFailure` 在 `:1070` 误判已绑定，跳过 `:1078` 重排队 |

**G13 / G14 / G15 → fixed。** 口诀：**账记上了才要退；失败重排队看 informer 的真相，不看调度器的副本。**

## 细颗粒第 3 步记录（2026-11-16）

对象：`schedulePod`（[`schedule_one.go:411-459`](https://github.com/kubernetes/kubernetes/blob/v1.32.0/pkg/scheduler/schedule_one.go#L411)）。它只是**编排函数**，自己不实现过滤/打分。

### 本轮问答与判定

| 题 | 你的答案 | 判定 | 纠正 |
|---|---|---|---|
| `ErrNoNodesAvailable` vs `FitError` | 前者 nodeinfo 为空即集群无节点；后者过了 filter 但没有可行节点；区别是是否经过 filter | 🟡 | 判断对，但未答**下游分支差异**（见下表） |
| `1 + diagnosis.NodeToStatus.Len()` | 不理解，猜「记录 prefilter/filter 过滤过的节点」 | 🟡 | 方向对。实际 = 可行节点 + 被 Filter 拒绝的节点，**只用于 `:325` 的 V(2) 日志**，不参与决策 |
| `trace.LogIfLong(100ms)` | 调度阈值，需要 klog ≥ 4 才能看到失败原因 | 🟡 | **日志级别说错**：走 `klog.Info`（V0），默认就打印；V(4) 只影响**步内细节**是否全打 |

### 四处短路（本步核心）

| 位置 | 条件 | 返回 | 后果 |
|---|---|---|---|
| `:414` | `UpdateSnapshot` 失败 | 原样 err | 走 `AsStatus` → Error |
| `:419` | 快照 0 节点 | `ErrNoNodesAvailable` | `:153` 特判 → `UnschedulableAndUnresolvable`，**跳过抢占** |
| `:429` | 可行节点 0 个 | `*FitError` | `:169` 起跑 PostFilter（**抢占**） |
| `:438` | 可行节点恰好 1 个 | 直接返回 | **跳过 `prioritizeNodes` 与 `selectHost`** |

`UnschedulableAndUnresolvable` = 「换什么节点都没用」；`Unschedulable` = 「暂时不行，资源变了再试」。

### 已澄清事实

1. `EvaluatedNodes = 可行节点数 + 被 Filter 拒绝的节点数`。单节点写 `1 + Len()`（`:441`），多节点写 `len(feasibleNodes) + Len()`（`:456`），同一公式。
2. `NodeToStatus` 由 `findNodesThatPassFilters` 在 `:664` 逐节点写入；`Len()`（`framework/interface.go:104`）只数 map 里的节点，**不含** `absentNodesStatus`。
3. `LogIfLong`（`k8s.io/utils/trace`）阈值语义：总耗时 ≥ 100ms 才打印，且直接用 `klog.Info`（**V0**），默认日志可见。`writeItem` 里 `stepDuration >= stepThreshold || klogV(4)` —— 开 V(4) 才打印**所有** step。
4. trace 只给**耗时**，不给失败原因。失败原因看 `FitError.Diagnosis`（`NodeToStatus` / `UnschedulablePlugins`），对外表现为 `FailedScheduling` 事件。

### 待答复测题

集群 3 个节点，Pod 调度失败：

1. 如果一个节点都没有 → 哪个出口？会不会抢占？
2. 如果 3 个节点都在但都因 `Insufficient cpu` 被拒 → 哪个出口？`EvaluatedNodes` 多少？
3. 第二种情况下默认日志级别能看到什么？开 `-v=4` 多看到什么？

### 复测结果（2026-11-18）

| # | 判定 | 要点 |
|---|---|---|
| 1 | ✅ | `ErrNoNodesAvailable` → `UnschedulableAndUnresolvable`，跳过抢占 |
| 2 | 🟡 | 出口是 `FitError`；默认 scheduler 有 PostFilter，`HasPostFilterPlugins()` 为 true，会跑抢占。`EvaluatedNodes = 0`（`schedulePod` 返回零值 `ScheduleResult`），实际节点数在 `FitError.NumAllNodes` |
| 3 | 🟡 | `trace.LogIfLong(100ms)` 走 `klog.Info`（V0），默认可见（总耗时 ≥100ms 时）；`-v=4` 打印所有 step。`logger.V(3)` 那行需要 `-v=3`；且场景 2 默认会走抢占，不进这个分支 |

### 待答追问

1. 场景 2 里默认 scheduler 有 `DefaultPreemption`（PostFilter），`schedulingCycle` 在 `:175` 跑完抢占后返回什么 Status？为什么不是 `UnschedulableAndUnresolvable`？
2. `trace.LogIfLong(100ms)` 在默认级别下**什么时候**能看到？`-v=4` 多看到什么？`logger.V(3)` 那行需要几级？

### 追问结果（2026-11-18）

| # | 判定 | 要点 |
|---|---|---|
| 1 | 🟡 → 已纠正 | 最终返回是 `framework.NewStatus(Unschedulable).WithError(err)`（`schedule_one.go:188`）；`WithPlugin(rejectorPlugin)` 在 `RunPostFilterPlugins` 内部（`framework.go:961`）。`UnschedulableAndUnresolvable` 不只「无节点」：PreFilter/Filter 也可返回（`framework.go:762/944`） |
| 2 | ✅ | 默认级别在总耗时 ≥100ms 时打印 trace（`klog.Info` V0）；`-v=4` 打印所有 step；`logger.V(3)` 需要 `-v=3` |

**G16 / G17 → fixed。第 3 步通过。**

## 追问复盘（2026-11-10 已答完）

| # | 结果 | 要点 |
|---|---|---|
| 追1 | ✅ fixed（G10 关闭） | 记账本是 `cache.go:67` 的 `assumedPods sets.Set[string]`；销账两条路：`AddPod`（成功，经过滤器把 Update 转译成 OnAdd）与 `ForgetPod`（失败）。三条出口全汇入 `removePod`（`cache.go:460`） |
| 追2 | ✅ fixed（G9 关闭） | `RunPermitPlugins` 不阻塞，只登记 `waitingPods` 后返回 Wait；阻塞发生在 `WaitOnPermit`（`framework.go:1514`），跑在 `schedule_one.go:120` 起的 binding goroutine 里 |

### 本轮新增已澄清事实

1. `FilteringResourceEventHandler.OnUpdate`（`staging/.../tools/cache/controller.go:313-326`）会把「过滤前 false → 过滤后 true」的 Update **转译成 OnAdd**。这就是「assumed 的 Pod 收到 Add 事件」的机制（见 `cache.go:532-533` 注释）。
2. `RemovePod`（`cache.go:546`）**不检查** `assumedPods`；`ForgetPod`（`cache.go:418-422`）**检查**。二者不对称是有意设计：前者代表外部事实删除，后者代表调度器主动退账。
3. `cleanupAssumedPods`（`cache.go:730`）默认**不生效**：`durationToExpireAssumedPod = 0`（`scheduler.go:58`），`ttl != 0` 条件不成立。
4. 删除事件有两个 handler：`deletePodFromCache`（`eventhandlers.go:376`）清 cache，`deletePodFromSchedulingQueue`（`:407`）清队列。
5. `schedulingCycle:231` 把 Permit 的 `Wait` 与 `Success` 同等对待；差别只在 `WaitOnPermit` 一侧。
6. 接口方法（如 `fwk.RunBindPlugins`）跳到 `interface.go` 的声明是正常的；实现在 `runtime/framework.go:1286`（`*frameworkImpl`）。
7. `bind`（`schedule_one.go:968`）**自身不发任何网络请求**：先试 extender（`extendersBinding`），再转给 `fwk.RunBindPlugins`（`framework.go:1286`）→ `DefaultBinder.Bind`（`default_binder.go:51`）→ `Pods(ns).Bind()`（`:58`）。
8. `FinishBinding`（`cache.go:376`）由 `defer` **总是执行**；不生效的是 `cleanupAssumedPods` 的删除动作。二者是两个独立开关。
9. `bindingFinished` = 绑定流程已结束；`deadline` = 允许 assumed 记账保留的截止时间。`ttl=0` 时 `deadline=nil` 且永不删除。

## 第 4 节复测结果（2026-11-10）

| # | 判定 | 缺口 |
|---|---|---|
| 1 | 🟡 模糊 | `Run` 只答出起 goroutine；漏 `SchedulingQueue.Run`（`scheduler.go:466`）与收尾 `Close`（`:476-480`）；入队链路完全未答（G1/G8） |
| 2 | 🟡 模糊 | 两个调用答对（`framework.go:1370` / `:1454`）；Wait 行为未答（G9） |
| 3 | ⬜ 空白 | 退账完全不清楚（`handleSchedulingFailure` @ `schedule_one.go:1023`）（G10） |

**结论**：三题全未过。随后通过 2 道追问 + 1 轮定点复测补齐 G9/G10（均已 fixed），G8 已答对可关。**G1 仍在，已升级 must-fix**（cache 与 queue 混用，出现 2 次以上）。

## 33 张卡状态

### Scheduler（T，16 张）

| 卡 | 名称 | 周次 | 状态 | 备注 |
|---|---|---|---|---|
| T0-1 | 让调度器说话 | W1 必做 | 🟡 有产出，未验收 | `logs/` 有 v=5 窗口与 describe |
| T0-2 | 亲手制造一次 FailedScheduling | W1 必做 | 🟡 有产出，未验收 | `logs/08–10` + 失败矩阵 |
| T1-1 | 追一个 Pod 的一生 | W1 必做 | 🔄 进行中 | 粗颗粒已过；细颗粒第 2、3 步已过，下一步第 4 步 `findNodesThatFitPod` |
| T1-2 | 找到那个 goroutine 的边界 | W1 弹性 | ⬜ 未开始 | 与 T1-1 第 4/12 步重叠 |
| T1-3 | 多个插件怎么合并成一个分数 | W2 弹性 | ⬜ 未开始 | |
| T2-0 | 先把 kube-scheduler 编译出来 | W2 必做 | ⬜ 未开始 | |
| T2-1 | 第一个插件：只打一行日志 | W2 必做 | ⬜ 未开始 | |
| T2-2 | 让分数真正决定 Pod 去哪 | W2 必做 | ⬜ 未开始 | |
| T2-3 | 从软偏好升级成硬约束 | W4 必做 | ⬜ 未开始 | |
| T2-4 | 给插件写单测 | W4 必做 | ⬜ 未开始 | |
| T3-1 | Permit：手写简化版 gang | W4 必做 | ⬜ 未开始 | |
| T3-2 | Unreserve：验证回滚幂等 | W7 弹性 | ⬜ 未开始 | |
| T3-3 | CycleState：跨扩展点传状态 | W4 弹性 | ⬜ 未开始 | |
| T4-1 | kwok 造 2000 节点压测 | 收口 | ⬜ 未开始 | |
| T4-2 | 一页纸压测报告 | 收口 | ⬜ 未开始 | |
| T5-1 | 一篇能发出去的文章 | W8 必做 | ⬜ 未开始 | |

状态图例：⬜ 未开始 / 🔄 进行中 / 🟡 有产出未验收 / ✅ 已验收。

### Volcano（V，8 张）

| 卡 | 名称 | 周次 | 状态 |
|---|---|---|---|
| V0-1 | 先确认它到底是不是 kube-scheduler 的 fork | W5 必做 | ⬜ 未开始 |
| V0-2 | 在集群里看一次真实的 gang 调度 | W5 必做 | ⬜ 未开始 |
| V0-3 | 排一次真实的调度失败（排障表） | W5 必做 | ⬜ 未开始 |
| V1-1 | 三抽象：Job / PodGroup / Queue | W6 必做 | ⬜ 未开始 |
| V1-2 | Session 机制 | W6 必做 | ⬜ 未开始 |
| V2-1 | gang 判定（对照 T3-1） | W6 必做 | ⬜ 未开始 |
| V2-2 | Queue 配额 | W7 必做 | ⬜ 未开始 |
| V3-1 | 给 Volcano 写 plugin | W7 必做 | ⬜ 未开始 |

### 大模型框架（M，9 张）

| 卡 | 名称 | 周次 | 状态 |
|---|---|---|---|
| M0-1 | 让 vLLM 吐出第一个 token | W3 必做 | ⬜ 未开始 |
| M0-2 | 打开张量并行 | W3 必做 | ⬜ 未开始 |
| M1-1 | PagedAttention 到底解决了什么 | W3 必做 | ⬜ 未开始 |
| M1-2 | 吞吐拐点 | W6 弹性 | ⬜ 未开始 |
| M2-1 | 3D 并行 | W7 必做 | ⬜ 未开始 |
| M2-2 | 跑一次分布式训练 | W7 弹性 | ⬜ 未开始 |
| M2-3 | checkpoint 的真实代价 | 建议 W7/W8 | ⬜ 未开始 |
| M3-1 | 训练任务对调度的真实要求 | 建议 W7/W8 | ⬜ 未开始 |
| M3-2 | 用 Volcano 调度一个真实训练任务（会师点） | W8 必做 | ⬜ 未开始 |

> 本次验收仍只做 T1-1；V/M 两条线分别在 W5 / W3 开始。

## T1-1 内部进度

- [x] 产出物形式核对：36 节点、位置齐全、三要素齐全
- [x] 第 1 步编排（`schedule_one.go:65`）
- [x] 函数字段机制：`NextPod = podQueue.Pop`；`SchedulePod` / `FailureHandler` 是字段
- [x] **粗颗粒 6 阶段口述（2026-11-12 通过）**
- [x] 细颗粒第 2 步（`schedulingCycle`，2026-11-15 通过）
- [x] 细颗粒第 3 步（`schedulePod`，2026-11-18 通过）
- [~] 细颗粒第 4 步（`findNodesThatFitPod`）
- [ ] 终检：不看图口述完整链路

## 盲区台账

| 编号 | 盲区 | 状态 |
|---|---|---|
| G1 | 把 `NextPod` 当「入队」；cache 与 queue 混用 | **open · must-fix** |
| G2 | 选节点整段缺失（`ScheduleOne` 后直接跳到 `assume`） | open |
| G3 | 把 `handleBindingCycleError` 当主干 | open |
| G4 | 把 `NewCycleState` 当 PreFilter / 认为它让 Pod 进 activeQ | open |
| G5 | 不清楚 `SchedulingQueue.Done` 的语义 | open |
| G6 | 失败出口函数名说错 | open |
| G7 | 不理解 `FailureHandler` / `SchedulePod` 是函数字段 | fixed |
| G8 | 认为 `Scheduler.Run` 负责收集待调度 Pod | fixed（本轮第 1 题答对） |
| G9 | 阶段 3 跳过 Reserve / Permit | fixed（追2） |
| G10 | 认为拆分绑定周期是为了避免「绑定失败却写入」 | fixed（追1） |
| G11 | 把 `FinishBinding` 当成「集群可见」标志 | fixed（2026-11-12） |
| G12 | PreFilter/Score 被当成独立阶段 | fixed（2026-11-12） |
| G13 | 误以为 `assume` 失败后要 `ForgetPod` | fixed（2026-11-15） |
| G14 | 误以为 `Permit` 失败不退账（与 `assume` 弄反） | fixed（2026-11-15） |
| G15 | 不知道 `DeepCopy` 的必要性 | fixed（2026-11-15） |
| G16 | 不知道 `ErrNoNodesAvailable` 与 `FitError` 会导致「是否抢占」的分叉 | fixed（2026-11-18） |
| G17 | 误以为 trace 需要 `-v=4`；混淆 trace（耗时）与 `FitError`（原因） | fixed（2026-11-18） |

## 会话日志

- **2026-11-07**：首次验收 T1-1。判完第 1 步 1-1 / 1-2 / 1-3；函数字段机制复测 A/B 通过（G7 关闭）；C/D 因粒度过细暂缓。
- **2026-11-09**：粒度改为先粗后细；生成 6 阶段主干；把任务包整理为自包含仓库并推送。同日补充 V（8 张）与 M（9 张）两条线路线图，仓库覆盖 33 张卡。
- **2026-11-09（续）**：完成粗颗粒 A/B/C，三题均判 🟡；新增 G8–G10；给出 3 道复测题。
- **2026-11-10**：克隆学习仓库到 `scheduler/scheduler/`。完成 `pkg/scheduler/` 三个核心文件的注释汉化（原地追加中文，不增删行，行数保持 589 / 1134 / 665）。由 `go build` 与 gofmt 验证通过；76 处文档行号引用经脚本全量核验仍有效。
- **2026-11-10（续）**：做第 4 节复测 3 题，判 🟡/🟡/⬜，均未过。追1 问「靠什么反查占坑」、追2 问「Permit Wait 是否阻塞主循环」，待答。
- **2026-11-10（末）**：追1/追2 均已答完并 fixed，G9/G10 关闭；G8 本轮答对也关闭。追1 过程中额外澄清了 assume 记账的三条出口、`FilteringResourceEventHandler` 把 Update 转译成 OnAdd 的机制、`RemovePod` 与 `ForgetPod` 的不对称、`cleanupAssumedPods` 默认不生效。G1（cache/queue 混用）本轮再现，升级 must-fix。
- **2026-11-12**：§4 的 A/B/C 第 3 次重测。首轮 B-3 误把 `FinishBinding` 当可见标志（G11 🔴），追问后修正为 `default_binder.go:58`；再确认 `bind` 自身不发请求后 G11 关闭。G12（PreFilter/Score 阶段归属）也修正。**粗颗粒 6 阶段层通过。** 同步生成 `docs/T1-1-pod-lifecycle-6stages.md`。
- **2026-11-13**：开细颗粒第 2 步（`schedulingCycle`）。`SchedulePod` 失败不退账、`Wait` 必须排除两项答对；但 `assume` 失败误答为「要清理缓存」、`Permit` 失败误答为「不退账」，两处弄反，新增 G13/G14（🔴），`DeepCopy` 原因未知记 G15（⬜）。待答 3 道复测题。
- **2026-11-15**：本机重新拉取 v1.32.0 源码。`eventhandlers.go` / `scheduler.go` / `schedule_one.go` 三个带注释的版本已还原为干净源码，带注释版本备份在本地 `.local-backup/`（未入库）。`pkg/scheduler` 与模块缓存逐文件一致，文档行号恢复有效。
- **2026-11-15（续）**：整理 `docs/SCHEDULER_STUDY_GUIDE.md`（T1-1 汇编版）。用模块缓存 `k8s.io/kubernetes@v1.32.0` 全量核对行号，修正旧记录中 6 处引用（`go func` 121→120、`handleSchedulingFailure` 1053→1023、单节点短路 437→438、`addPodToCache` 215→203、`RunReservePluginsUnreserve` 1298→1414、Score 并发粒度表述）。顺带补查 T0-2 交付物：`FailedScheduling` 消息由 `framework/types.go:520` + `FitError.Error()`（`:543-593`）拼出。
- **2026-11-15（晚）**：重做三个核心文件的注释汉化（`scheduler.go` / `schedule_one.go` / `eventhandlers.go`）。译文挂在每个英文注释块最后一行，行数保持 589 / 1134 / 665，49 / 95 / 28 个注释块全部覆盖。`gofmt -l` 无输出、`go build ./pkg/scheduler/` 通过、逐行前缀校验 0 违例。干净原件存 `.local-backup/clean/`，同版本备份已更新到 `.local-backup/`。
- **2026-11-15（夜）**：把汉化扩到 9 个核心文件（新增 `cache.go` / `scheduling_queue.go` / `framework/interface.go` / `framework/types.go` / `framework/runtime/framework.go` / `default_binder.go`），共 792 个注释块、8535 行，行数全部不变。新增 `scripts/annotate_comments.py`（单文件列块/应用/校验）、`scripts/apply_annotations.py` + `apply-annotations.sh/.ps1`（按 manifest 一键恢复）、`scripts/annotations/`（9 份译文映射）。校验：9 个文件 `--check` 全过、`gofmt` 无输出、`go build ./pkg/scheduler/...` 通过、映射重放与当前文件逐字节一致。
- **2026-11-15（学习收口）**：完成细颗粒第 2 步复测：`assume` 失败不退账 ✅、`Reserve`/`Permit` 失败退账 ✅、`DeepCopy` 防 informer 污染 ✅。G13/G14/G15 关闭。生成复盘笔记 `docs/review-2026-11-15.md`。
- **2026-11-16**：开细颗粒第 3 步（`schedulePod`）。三题均 🟡：`ErrNoNodesAvailable`/`FitError` 的区分判断对但未答抢占分支；`EvaluatedNodes` 公式只猜出一半；trace 日志级别说成需要 `-v=4`（实际 `klog.Info` V0）。新增 G16/G17。顺带修正 `go func` 行号 121→120。
- **2026-11-18（第 3 步复测）**：Q1 ✅；Q2 🟡（漏默认 PostFilter/抢占、`EvaluatedNodes=0`）；Q3 🟡（默认级别与 V3/V4 说错，G17 复现，升级 must-fix）。待答 2 道追问。
- **2026-11-18**：本机拉取远端最新 `03ea59b`，同步第 3 步记录；再次用模块缓存恢复 9 个核心文件为干净 v1.32.0，`pkg/scheduler` 与模块缓存逐文件一致。注释映射保留在 `scripts/annotations/`。
- **2026-11-18（第 3 步收口）**：追问答完；纠正最终 Status 为 `NewStatus(Unschedulable).WithError(err)`（`:188`），`WithPlugin` 在 `RunPostFilterPlugins`（`framework.go:961`）；确认 trace 默认阈值与 V3/V4 关系。G16/G17 关闭，第 3 步通过。
- **2026-11-18（复盘）**：生成 `docs/review-2026-11-18.md`，覆盖 `schedulePod` 四短路、`ErrNoNodesAvailable`/`FitError`、trace vs FitError、PreFilter/Filter/PostFilter 分工。
- **2026-11-18（练习）**：新增 `docs/worksheet-T1-1-flowchart.md`，把 6 阶段、`ScheduleOne` 分叉、`schedulePod` 四短路、PreFilter/Filter/PostFilter 做成填空图。
- **2026-11-18（流程规范）**：固化「每步开始先给填空版组件流程图」到 skill / `AGENTS.md`；worksheet 增加第 4 步 `findNodesThatFitPod` 的图 5（PreFilter 三种 Status / NominatedNode / Diagnosis）。
- **2026-11-22**：把汉化扩到调度器全部非测试源码：`pkg/scheduler/**`、`cmd/kube-scheduler/**`、`staging/k8s.io/kube-scheduler/**`，共 124 个文件、34,144 行、3,032 个注释块（3,033 条译文）。映射写入 `scripts/annotations/` 并登记到 manifest；`apply_annotations.py` 增加只读文件处理与「已汉化也校验」。验收：124 个文件 `--check` 全过、`gofmt` 无输出、`go build ./pkg/scheduler/... ./cmd/kube-scheduler/...` 通过、行数与 v1.32.0 上游逐文件一致。

## 更新规则

每次会话结束必须更新四处：

1. 「最近更新」日期。
2. 「下次入口」。
3. 「T1-1 内部进度」的勾选状态。
4. 新增/关闭的盲区，以及「会话日志」追加一行。
