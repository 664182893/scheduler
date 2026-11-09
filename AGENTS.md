# Agent 指南（kube-scheduler 学习工作区）

本仓库是一个**学习型**工作区，不是生产代码库。主要活动是：读源码 → 用户口述 → 判定理解 → 记录盲区。

## 每次会话开始

1. 读 `progress.md`，找到「下次入口」。
2. 读 `plan/scheduler-roadmap.md` 里当前任务（现在通常是 T1-1）的原文。**这是唯一考纲**。
3. 读 `acceptance/` 下当前任务的文件和最近一次验收记录。
4. 按 `.agents/skills/dialogue-acceptance/SKILL.md` 的流程继续：先补答快照里的「待答」，再进下一步。

## 硬规则

- **考纲只来自 `plan/scheduler-roadmap.md`**，不要用 `docs/` 里的产出物反推范围，也不要自拟考纲。
- **先粗后细**：主干没通时，缓存、goroutine、数据结构、插件内部一律标「暂缓」，不判失败。
- **每个判定必须指回 `文件:行号`**（源码版本固定 v1.32.0）。
- 用户答错先追问一次，再纠正；不奉承，不把「看过文档」当「理解」。
- 一次只问 3–5 题，等回答后再出下一轮。
- 每次会话结束更新 `progress.md`：最近更新、当前任务、待答、新盲区、下次入口。
- 不要提交 `pkg/`、`staging/`、`test/`、`cmd/`、`go.mod`、`go.sum`、`LICENSE`（见 `.gitignore`）。
- 不要把源码快照、原始大日志推进仓库。

## 常见操作

```bash
# 拉源码（Git Bash / macOS / Linux）
bash scripts/setup-source.sh

# Windows PowerShell
powershell -File scripts/setup-source.ps1

# 核对行号（示例）
sed -n '65p' kubernetes-v1.32.0/pkg/scheduler/schedule_one.go
```

## 当前进度入口

- 任务：T1-1「追一个 Pod 的一生」
- 粒度：粗颗粒 6 阶段
- 待答：`acceptance/T1-1-pod-lifecycle.md` 第 4 节 A/B/C
- 下一步：答完 A/B/C → 细颗粒 12 步（第 2 步 `schedule_one.go:138`）→ 终检口述全链
