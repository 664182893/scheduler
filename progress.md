# 进度总表

- 最近更新：2026-11-11
- 当前任务：**T1-1 追一个 Pod 的一生**
- 当前粒度：**粗颗粒（6 阶段）**
- 源码版本：kube-scheduler v1.32.0
- 源码位置：`D:\code\GoCode\src\scheduler\k8s-v1.32.0`（仓库外，独立 git 仓库）
- 注释汉化：`scheduler.go` / `schedule_one.go` / `eventhandlers.go` 已完成（追加式，行号不变）

## 下次入口

1. **G1 定点练习**（3 分钟）：cache / queue / `NextPod` 三者切分。G1 已升级 must-fix（出现 ≥2 次）。
2. 然后重测 §4 的 A/B/C 三题；全过则粗颗粒层通过。
3. 通过后进入细颗粒 12 步，从第 2 步 `schedule_one.go:138` 开始。
4. 12 步走完做终检：不看图口述完整链路。

## 追问复盘（2026-11-10 已答完）

| # | 结果 | 要点 |
|---|---|---|
| 追1 | ✅ fixed（G10 关闭） | 记账本是 `cache.go:67` 的 `assumedPods sets.Set[string]`；销账两条路：`AddPod`（成功，经过滤器把 Update 转译成 OnAdd）与 `ForgetPod`（失败）。三条出口全汇入 `removePod`（`cache.go:460`） |
| 追2 | ✅ fixed（G9 关闭） | `RunPermitPlugins` 不阻塞，只登记 `waitingPods` 后返回 Wait；阻塞发生在 `WaitOnPermit`（`framework.go:1514`），跑在 `schedule_one.go:121` 起的 binding goroutine 里 |

### 本轮新增已澄清事实

1. `FilteringResourceEventHandler.OnUpdate`（`staging/.../tools/cache/controller.go:313-326`）会把「过滤前 false → 过滤后 true」的 Update **转译成 OnAdd**。这就是「assumed 的 Pod 收到 Add 事件」的机制（见 `cache.go:532-533` 注释）。
2. `RemovePod`（`cache.go:546`）**不检查** `assumedPods`；`ForgetPod`（`cache.go:418-422`）**检查**。二者不对称是有意设计：前者代表外部事实删除，后者代表调度器主动退账。
3. `cleanupAssumedPods`（`cache.go:730`）默认**不生效**：`durationToExpireAssumedPod = 0`（`scheduler.go:58`），`ttl != 0` 条件不成立。
4. 删除事件有两个 handler：`deletePodFromCache`（`eventhandlers.go:376`）清 cache，`deletePodFromSchedulingQueue`（`:407`）清队列。
5. `schedulingCycle:231` 把 Permit 的 `Wait` 与 `Success` 同等对待；差别只在 `WaitOnPermit` 一侧。
6. 接口方法（如 `fwk.RunBindPlugins`）跳到 `interface.go` 的声明是正常的；实现在 `runtime/framework.go:1286`（`*frameworkImpl`）。

## 第 4 节复测结果（2026-11-10）

| # | 判定 | 缺口 |
|---|---|---|
| 1 | 🟡 模糊 | `Run` 只答出起 goroutine；漏 `SchedulingQueue.Run`（`scheduler.go:466`）与收尾 `Close`（`:476-480`）；入队链路完全未答（G1/G8） |
| 2 | 🟡 模糊 | 两个调用答对（`framework.go:1370` / `:1454`）；Wait 行为未答（G9） |
| 3 | ⬜ 空白 | 退账完全不清楚（`handleSchedulingFailure` @ `schedule_one.go:1053`）（G10） |

**结论**：三题全未过。随后通过 2 道追问 + 1 轮定点复测补齐 G9/G10（均已 fixed），G8 已答对可关。**G1 仍在，已升级 must-fix**（cache 与 queue 混用，出现 2 次以上）。

## 33 张卡状态

### Scheduler（T，16 张）

| 卡 | 名称 | 周次 | 状态 | 备注 |
|---|---|---|---|---|
| T0-1 | 让调度器说话 | W1 必做 | 🟡 有产出，未验收 | `logs/` 有 v=5 窗口与 describe |
| T0-2 | 亲手制造一次 FailedScheduling | W1 必做 | 🟡 有产出，未验收 | `logs/08–10` + 失败矩阵 |
| T1-1 | 追一个 Pod 的一生 | W1 必做 | 🔄 进行中 | 追问已清 G9/G10；待做 G1 定点练习 → 重测 A/B/C |
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
- [~] 粗颗粒 6 阶段口述：追问已清 G9/G10；A/B/C 仍需重测（卡在 G1）
- [ ] 细颗粒 12 步（第 2–12 步）
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

## 会话日志

- **2026-11-07**：首次验收 T1-1。判完第 1 步 1-1 / 1-2 / 1-3；函数字段机制复测 A/B 通过（G7 关闭）；C/D 因粒度过细暂缓。
- **2026-11-09**：粒度改为先粗后细；生成 6 阶段主干；把任务包整理为自包含仓库并推送。同日补充 V（8 张）与 M（9 张）两条线路线图，仓库覆盖 33 张卡。
- **2026-11-09（续）**：完成粗颗粒 A/B/C，三题均判 🟡；新增 G8–G10；给出 3 道复测题。
- **2026-11-10**：克隆学习仓库到 `scheduler/scheduler/`。完成 `pkg/scheduler/` 三个核心文件的注释汉化（原地追加中文，不增删行，行数保持 589 / 1134 / 665）。由 `go build` 与 gofmt 验证通过；76 处文档行号引用经脚本全量核验仍有效。
- **2026-11-10（续）**：做第 4 节复测 3 题，判 🟡/🟡/⬜，均未过。追1 问「靠什么反查占坑」、追2 问「Permit Wait 是否阻塞主循环」，待答。
- **2026-11-10（末）**：追1/追2 均已答完并 fixed，G9/G10 关闭；G8 本轮答对也关闭。追1 过程中额外澄清了 assume 记账的三条出口、`FilteringResourceEventHandler` 把 Update 转译成 OnAdd 的机制、`RemovePod` 与 `ForgetPod` 的不对称、`cleanupAssumedPods` 默认不生效。G1（cache/queue 混用）本轮再现，升级 must-fix。

## 更新规则

每次会话结束必须更新四处：

1. 「最近更新」日期。
2. 「下次入口」。
3. 「T1-1 内部进度」的勾选状态。
4. 新增/关闭的盲区，以及「会话日志」追加一行。
