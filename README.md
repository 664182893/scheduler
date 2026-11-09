# 调度学习工作区（33 张任务卡：scheduler / Volcano / 大模型框架）

一个自包含的调度学习工作区，覆盖三条线共 33 张任务卡。换电脑后：clone 本仓库 → 跑一个脚本拉源码 → 从 `progress.md` 的「下次入口」继续。

| 线 | 定位 | 任务卡 |
|---|---|---|
| Scheduler（T） | 调度的地基：单个 Pod 怎么选节点 | 16 张 |
| Volcano（V） | 你集群里真正在跑的那层：一批 Pod 怎么一起动 | 8 张 |
| 大模型框架（M） | 被调度的负载：它对调度提了哪些要求 | 9 张 |

三线的会师点：**Volcano 调一个真实训练任务**（M3-2），而不是自己写插件调玩具任务。

## 从这里开始

1. **`progress.md`** —— 当前做到哪、下一步是什么、还有哪些盲区。
2. **`plan/`** —— 三条线共 33 张任务卡的考纲（问题 / 动作 / 交付 / 验收 / 卡点）：
   - `plan/scheduler-roadmap.md`（T，16 张）
   - `plan/volcano-roadmap.md`（V，8 张）
   - `plan/lm-roadmap.md`（M，9 张）
3. **`acceptance/`** —— 当前任务单和完整验收记录。
4. **拉源码**（二选一）：
   - macOS / Linux / Git Bash：`bash scripts/setup-source.sh`
   - Windows PowerShell：`powershell -File scripts/setup-source.ps1`
5. **让 agent 继续**，直接对 Zed 说：
   > 继续 scheduler 学习：先读 `progress.md`，从「下次入口」接着走，按 `.agents/skills/dialogue-acceptance/SKILL.md` 验收。

## 仓库结构

| 路径 | 用途 |
|---|---|
| `progress.md` | 全局进度：16 张卡状态、当前任务、待答、盲区、下次入口 |
| `plan/scheduler-roadmap.md` | T 系列 16 张任务卡原文（考纲，勿改） |
| `plan/volcano-roadmap.md` | V 系列 8 张任务卡原文 |
| `plan/lm-roadmap.md` | M 系列 9 张任务卡原文 |
| `acceptance/T1-1-pod-lifecycle.md` | 当前任务单（可复用模板） |
| `acceptance/2026-11-07-scheduler-callchain.md` | T1-1 完整验收记录 |
| `docs/SCHEDULER_CALLCHAIN.md` | 主干调用链（36 个节点，带行号） |
| `docs/SCHEDULER_FAILURE_MATRIX.html` | 同步 / 异步失败与回滚矩阵 |
| `docs/SOURCE_SNAPSHOT.md` | 源码快照的来源、版本、日志行号对照 |
| `logs/` | W1 用到的调度日志关键片段 |
| `scripts/setup-source.*` | 拉取 kube-scheduler v1.32.0 源码 |
| `.agents/skills/dialogue-acceptance/SKILL.md` | 对话式验收方法（项目内副本） |

## 学习路线（W1–W8）

| 周 | 必做 | 弹性 |
|---|---|---|
| W1 | T0-1 日志链路 / T0-2 制造失败 / T1-1 追一个 Pod 的一生 | T1-2 goroutine 边界 |
| W2 | T2-0 编译 / T2-1 插件打日志 / T2-2 分数决定落点 | T1-3 分数合并 |
| W3 | M0-1 第一个 token / M0-2 打开 TP / M1-1 PagedAttention（值班周） | — |
| W4 | T2-3 改写成 Filter / T2-4 单测 / T3-1 手写 gang | T3-3 CycleState |
| W5 | V0-1 验证非 fork / V0-2 看真实 gang / V0-3 排障表 | — |
| W6 | V1-1 三抽象 / V1-2 Session / V2-1 gang 判定（值班周） | M1-2 |
| W7 | V2-2 Queue 配额 / M2-1 3D 并行 / V3-1 写 Volcano 插件 | T3-2 / M2-2 |
| W8 | M3-2 会师 / T5-1 发文章 / 简历 / 模拟面试 | — |
| 收口 | T4-1 kwok 压测 / T4-2 压测报告 | — |

完整内容见 `plan/` 下三份路线图。M2-3、M3-1 未在周次表单列，建议放在 W7/W8 或作为弹性卡。

## 当前状态（2026-11-09）

- 当前任务：**T1-1 追一个 Pod 的一生**
- 当前粒度：**粗颗粒 6 阶段**（细节暂缓）
- 卡在：`acceptance/T1-1-pod-lifecycle.md` 第 4 节的 A / B / C 三题
- 下一步：答完 A/B/C → 细颗粒 12 步（从第 2 步 `schedule_one.go:138` 开始）→ 终检「不看图口述全链」

## 源码版本

- kube-scheduler **v1.32.0**，与集群一致。
- 所有 `文件:行号` 都基于该版本。版本不一致时行号会偏，先核对版本再看行号。
- 源码不随仓库提交（约 21MB 的 k8s 源码，且可随时拉取），用 `scripts/setup-source.*` 获取。

## 验收方式

- 对话式逐轮提问，判定 ✅ 掌握 / 🟡 模糊 / 🔴 误解 / ⬜ 空白。
- 每个判定必须指回 `文件:行号`。
- **先粗后细**：主干没通之前，不考 cache、goroutine、数据结构细节。
- 每次会话结束必须更新 `progress.md`。

## 不包含

- k8s 源码本体（脚本拉取）。
- 大体量原始日志（`logs/` 只保留关键片段；完整日志可用 `kubectl logs` / `docker cp` 重新采集）。
