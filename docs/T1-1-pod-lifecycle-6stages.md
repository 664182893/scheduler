# T1-1 · 粗颗粒主干：一个 Pod 的 6 个阶段

> 源码版本：kube-scheduler **v1.32.0**
> 源码根：`D:\code\GoCode\src\scheduler\k8s-v1.32.0`
> 所有行号已在该快照上逐条核对。注释已汉化（追加式），英文原文保留在中文之前。

记忆抓手：**入队 → 出队 → 选节点 → 占坑 → 绑定 → 收尾**

---

## 阶段 0 · 入队：Informer → activeQ

触发源是 informer 的 Add 事件，不是调度器主动扫描。

| 步骤 | 位置 | 职责 |
|---|---|---|
| 1 | [`eventhandlers.go:126`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/eventhandlers.go#L126) `addPodToSchedulingQueue` | informer 回调，接收未绑定 Pod |
| 2 | [`scheduling_queue.go:598`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/backend/queue/scheduling_queue.go#L598) `PriorityQueue.Add` | 放进 activeQ |

**注意**：这一阶段和 cache 无关。cache 回答「放不放得下」，队列回答「下一个轮到谁」。

---

## 阶段 1 · 出队：启动循环并取 Pod

| 步骤 | 位置 | 职责 |
|---|---|---|
| 1 | [`scheduler.go:464`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/scheduler.go#L464) `Run` | 启动队列（`:466`）、起单 goroutine 循环（`:474`）、阻塞等退出 |
| 2 | [`schedule_one.go:65`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L65) `ScheduleOne` | 单个 Pod 的完整调度编排 |
| 3 | [`schedule_one.go:67`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L67) `NextPod` | 阻塞出队（赋值在 `scheduler.go:378`） |
| 4 | [`scheduling_queue.go:857`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/backend/queue/scheduling_queue.go#L857) `Pop` | 真正的出队实现 |

**关键**：`scheduler.go:474` 只有一个 goroutine 跑 `ScheduleOne`。任何在这条主路径上阻塞的操作都会让整个集群调度停摆。

---

## 阶段 2 · 选节点：过滤 → 打分 → 选最高

这一阶段的边界是 `schedulePod` 到 `selectHost`。**PreFilter / Filter / PreScore / Score 全都嵌在这一阶段内部，不是独立阶段。**

| 步骤 | 位置 | 职责 |
|---|---|---|
| 1 | [`schedule_one.go:411`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L411) `schedulePod` | 选节点入口 |
| 2 | [`schedule_one.go:463`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L463) `findNodesThatFitPod` | 过滤内外层容器 |
| 3 | [`framework.go:709`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/runtime/framework.go#L709) `RunPreFilterPlugins` | 嵌在 `findNodesThatFitPod` 内 |
| 4 | [`schedule_one.go:591`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L591) `findNodesThatPassFilters` | 逐节点跑 Filter |
| 5 | [`schedule_one.go:755`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L755) `prioritizeNodes` | 打分编排 |
| 6 | [`framework.go:1112`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/runtime/framework.go#L1112) `RunScorePlugins` | 嵌在 `prioritizeNodes` 内 |
| 7 | [`schedule_one.go:873`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L873) `selectHost` | 从最高分中蓄水池采样选一个 |

**短路点**：[`schedule_one.go:437`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L437) —— 只剩一个可行节点时直接返回，PreScore/Score 整体跳过。单节点集群里调度只要 0.5ms 就是这个原因。

---

## 阶段 3 · 占坑：cache 记账 + 插件预留 / 放行

| 步骤 | 位置 | 职责 |
|---|---|---|
| 1 | [`schedule_one.go:946`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L946) `assume` | 写 `Spec.NodeName` + cache 记账 |
| 2 | [`cache.go:361`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/backend/cache/cache.go#L361) `AssumePod` | 节点资源扣减，`assumedPods` 插入 key |
| 3 | [`framework.go:1370`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/runtime/framework.go#L1370) `RunReservePluginsReserve` | 插件级预留 |
| 4 | [`framework.go:1454`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/runtime/framework.go#L1454) `RunPermitPlugins` | 插件放行判断；**返回 Wait 时不阻塞**，只登记 `waitingPods`（`:1493-1498`） |

这一阶段结束后，调度器「内部认为」Pod 已属于该节点，但 apiserver 还一无所知。

---

## 阶段 4 · 绑定：异步写 apiserver

在**独立的 goroutine** 里执行，`ScheduleOne` 不等待它。

| 步骤 | 位置 | 职责 |
|---|---|---|
| 1 | [`schedule_one.go:121`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L121) `go func()` | 起 binding goroutine |
| 2 | [`schedule_one.go:266`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L266) `bindingCycle` | 绑定周期编排 |
| 3 | [`framework.go:1514`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/runtime/framework.go#L1514) `WaitOnPermit` | **唯一真正阻塞的地方**，`<-waitingPod.s` |
| 4 | [`framework.go:1243`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/runtime/framework.go#L1243) `RunPreBindPlugins` | 绑定前插件 |
| 5 | [`schedule_one.go:968`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L968) `bind` | 先试 extender，再走框架（`:978`） |
| 6 | [`framework.go:1286`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/runtime/framework.go#L1286) `RunBindPlugins` | 遍历 Bind 插件，第一个非 Skip 的赢 |
| 7 | [`default_binder.go:51`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/plugins/defaultbinder/default_binder.go#L51) `DefaultBinder.Bind` | 默认绑定插件 |
| 8 | [`default_binder.go:58`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/plugins/defaultbinder/default_binder.go#L58) `Pods(ns).Bind()` | **真正写 apiserver，集群可见以这一行为准** |

> 接口方法跳转会停在 [`interface.go:751`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/interface.go#L751) 的声明处，这是正常的；`Framework` 接口定义在 `interface.go:686`，唯一实现是 `*frameworkImpl`（`framework.go:52`）。

---

## 阶段 5 · 收尾

| 步骤 | 位置 | 职责 |
|---|---|---|
| 1 | [`schedule_one.go:1000`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L1000) `finishBinding` | `defer` 执行，成败都跑 |
| 2 | [`cache.go:376`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/backend/cache/cache.go#L376) `FinishBinding` | 只置标记，**不销账**（见下节） |
| 3 | [`framework.go:1335`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/runtime/framework.go#L1335) `RunPostBindPlugins` | 绑定后插件 |

---

## 三个时间点（易混，务必分清）

| 问题 | 时刻 | 代码 |
|---|---|---|
| 节点被**决定** | `selectHost` 返回 | [schedule_one.go:873](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L873) |
| 调度器**内部认为**已属该节点 | `assume` 写完 | [schedule_one.go:946](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L946) |
| 集群**真正可见** | `Bind` 成功返回后 | [default_binder.go:58](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/plugins/defaultbinder/default_binder.go#L58) |

`FinishBinding` **不是**可见标志，也不是销账点。

---

## 失败与退账

`assume` 是「借」，销账是「还」。三条出口最终都汇到 `removePod`。

| 场景 | 入口 | 链 |
|---|---|---|
| 绑定失败 | [`schedule_one.go:345`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/schedule_one.go#L345) `handleBindingCycleError` | `RunReservePluginsUnreserve`（[framework.go:1414](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/framework/runtime/framework.go#L1414)）→ `Cache.ForgetPod`（[cache.go:404](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/backend/cache/cache.go#L404)）→ 重新入队 |
| 绑定成功 | [`eventhandlers.go:215`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/eventhandlers.go#L215) `addPodToCache` | `Cache.AddPod` → assumed 分支（[cache.go:496](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/backend/cache/cache.go#L496)）→ `updatePod` → `removePod` |
| Pod 被删除 | [`eventhandlers.go:282`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/eventhandlers.go#L282) `deletePodFromCache` | `Cache.RemovePod`（[cache.go:546](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/backend/cache/cache.go#L546)）→ `removePod` |

销账点统一在 [`cache.go:460`](file:///D:/code/GoCode/src/scheduler/k8s-v1.32.0/pkg/scheduler/backend/cache/cache.go#L460) `removePod`，末尾 `delete(assumedPods)`（`:481`）。

> 隐藏机制：绑定成功后 informer 送来的是 **MODIFIED**，但 `FilteringResourceEventHandler.OnUpdate`（`staging/.../tools/cache/controller.go:313-326`）会把「过滤前 false → 过滤后 true」的更新**转译成 OnAdd**。这就是「assumed 的 Pod 会收到 Add 事件」的原因（见 `cache.go:532-533` 注释）。

---

## 为什么要拆成两个周期

| # | 理由 | 依据 |
|---|---|---|
| 1 | 绑定是远程 I/O，同步做会阻塞**唯一**的主调度循环 | `scheduler.go:474` 单 goroutine |
| 2 | `Permit` 可能返回 Wait（gang / 外部审批），不能占着主循环干等 | `framework.go:1493-1498` |

代价是引入了 optimistic concurrency：先占坑、后落地、失败退账。

---

## 一页速查

```
informer Add
  → addPodToSchedulingQueue (eventhandlers.go:126)
  → PriorityQueue.Add       (scheduling_queue.go:598)
        ↓
  Scheduler.Run (scheduler.go:464)  单 goroutine 循环
  → ScheduleOne (schedule_one.go:65)
  → NextPod/Pop (scheduler_queue.go:857)
  → schedulePod (411)
       ├ findNodesThatFitPod (463) ─ RunPreFilterPlugins (framework.go:709) ─ findNodesThatPassFilters (591)
       ├ prioritizeNodes (755) ──── RunScorePlugins (framework.go:1112)
       └ selectHost (873)
  → assume (946) ─ AssumePod (cache.go:361)
  → RunReservePluginsReserve (framework.go:1370)
  → RunPermitPlugins (framework.go:1454)
        ↓
  go func (121) → bindingCycle (266)
  → WaitOnPermit (framework.go:1514)   ← 唯一阻塞点
  → RunPreBindPlugins (framework.go:1243)
  → bind (968) → RunBindPlugins (framework.go:1286)
              → DefaultBinder.Bind (default_binder.go:51)
              → Pods(ns).Bind()      (default_binder.go:58)  ← 集群可见
        ↓
  finishBinding (1000) → FinishBinding (cache.go:376) → RunPostBindPlugins (framework.go:1335)
```
