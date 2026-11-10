# kube-scheduler v1.32.0 源码快照

与集群中运行的 scheduler 版本一致（`kubectl version` → server `v1.32.0`，镜像 `registry.k8s.io/kube-scheduler:v1.32.0`）。

## 来源

| 项 | 值 |
|---|---|
| 模块 | `k8s.io/kubernetes@v1.32.0`（等同 GitHub tag `v1.32.0`） |
| 下载方式 | `GOPROXY=https://goproxy.cn` + `go mod download k8s.io/kubernetes@v1.32.0` |
| 校验和 | `h1:4BDBWSolqPrv8GC3YfZw0CJvh5kA1TPnoX0FxDVd+qc=` |
| 调度器配置 API | `k8s.io/kube-scheduler@v0.32.0`（Kubernetes 1.32 对应 staging 模块 v0.32.x） |

## 目录

```
scheduler/
├── pkg/scheduler/                 # 调度器主体（193 个文件）
│   ├── scheduler.go               # 入口、event handler 注册
│   ├── schedule_one.go            # 单个 Pod 的调度循环（核心）
│   ├── eventhandlers.go           # informer 事件 → 调度队列
│   ├── backend/
│   │   ├── queue/                 # 调度队列（activeQ / backoffQ / unschedulablePods）
│   │   └── cache/                 # 节点快照缓存、assume/bind 状态
│   ├── framework/                 # 调度框架：runtime、cycle state、插件注册
│   │   └── plugins/               # 各内置插件（noderesources、nodeaffinity、defaultbinder...）
│   ├── apis/config/               # KubeSchedulerConfiguration 内部类型
│   ├── profile/                   # Profile（多调度器实例）
│   └── metrics/                   # 指标定义
├── cmd/kube-scheduler/            # 程序入口、命令行参数、options
├── staging/k8s.io/kube-scheduler/ # 配置 API 的 v1/v1beta3 类型定义
└── LICENSE                        # Apache-2.0
```

> 说明：这是本地源码工作副本，位于 `D:\code\GoCode\src\scheduler\k8s-v1.32.0`（独立 git 仓库，tag `v1.32.0`）。实测 `go build ./pkg/scheduler/` 通过（Go 1.23.0）。
>
> **注意目录层级**：仓库默认的 `scripts/setup-source.ps1` 会把源码拉到 `<本仓库>/kubernetes-v1.32.0/`，但当前实际快照在**仓库外**的上一级 `k8s-v1.32.0/`。本文所有 `文件:行号` 均以 `k8s-v1.32.0/pkg/scheduler/` 为准。

## 注释汉化（2026-11-10）

`pkg/scheduler/` 下三个核心文件已完成中英对照汉化：**在原英文注释行末尾追加中文译文，英文原文保留，不增删任何行**。

| 文件 | 总行数 | 汉化处数 |
|---|---|---|
| `scheduler.go` | 589 | 93 |
| `schedule_one.go` | 1134 | 180 |
| `eventhandlers.go` | 665 | 84 |

正因为「只追加、不增行」，**本文所有 `文件:行号` 在汉化后依然精确有效**，无需换算。校验方式：

```bash
cd D:/code/GoCode/src/scheduler/k8s-v1.32.0
diff <(git show HEAD:pkg/scheduler/schedule_one.go | sed -E 's#//.*$##') ...
gofmt -l pkg/scheduler/     # 无输出 = 格式合规
```

格式约定：`// English original. // 中文译文`；空注释行保持纯 `//`；许可头、`//go:build`、`//nolint` 不译。

## 日志行号 → 源码（对应本次 v=5 日志）

`scheduler_wpk8s` 日志里 `file.go:line` 那一列可以直接在本目录定位：

| 日志中的位置 | 源码级别 | 消息 |
|---|---|---|
| `eventhandlers.go:132` | V(3) | `Add event for unscheduled pod` |
| `eventhandlers.go:186` | V(3) | `Delete event for unscheduled pod` |
| `eventhandlers.go:214` | V(3) | `Add event for scheduled pod` |
| `eventhandlers.go:251` | V(4) | `Update event for scheduled pod` |
| `scheduling_queue.go:587` | V(5) | `Pod moved to an internal scheduling queue` |
| `schedule_one.go:83` | V(4) | `About to try and schedule pod` |
| `schedule_one.go:99` | V(3) | `Attempting to schedule pod` |
| `default_binder.go:53` | V(3) | `Attempting to bind pod to node` |
| `cache.go:390` | V(5) | `Finished binding for pod, can be expired` |
| `schedule_one.go:325` | V(2) | `Successfully bound pod to node` |
| `framework.go:399` | V(2) | `the scheduler starts to work with those plugins` |

## 两个和日志分析直接相关的结论

1. **单节点时不做打分**：`schedule_one.go:437-444`

   ```go
   // When only one node after predicate, just use it.
   if len(feasibleNodes) == 1 {
       return ScheduleResult{SuggestedHost: feasibleNodes[0].Node().Name, ...}, nil
   }
   ```

   这就是 kind 单节点集群里调度只花 0.5ms、日志直接跳到 `Attempting to bind` 的原因——PreScore/Score 阶段被整体跳过。

2. **逐插件得分只在 V(10) 且有多个候选节点时才打印**：`schedule_one.go:788-796`

   ```go
   loggerVTen := logger.V(10)
   if loggerVTen.Enabled() {
       for _, nodeScore := range nodesScores {
           for _, pluginScore := range nodeScore.Scores {
               loggerVTen.Info("Plugin scored node for pod", "pod", ..., "plugin", ..., "score", ...)
           }
       }
   }
   ```

   之前 `--v=10` 看不到 `Plugin scored node for pod`，正是因为只有一个可行节点，代码在上面的 `len(feasibleNodes) == 1` 处提前返回了。想看到插件打分，必须至少两个可行节点。
