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

> 说明：源码副本位置因机器而异：
> - **本机（2026-11-15）**：仓库根就是源码根，即 `pkg/scheduler/`；路径记录在 `.agents/source-root.local`。
> - 另一台机器：`D:\code\GoCode\src\scheduler\k8s-v1.32.0`（独立 git 仓库，tag `v1.32.0`）。
> - `scripts/setup-source.*` 默认拉取到 `<本仓库>/kubernetes-v1.32.0/`。
>
> 本文所有 `文件:行号` 均以 v1.32.0 的 `pkg/scheduler/` 为准，与源码根放在哪里无关。

## 注释汉化（2026-11-22 全量）

调度器相关**全部 Go 源码**（含 `_test.go`）已完成中英对照汉化：`//` 注释在英文后追加 ` // 中文`，`/* ... */` 注释在块内追加中文；行数完全不变。

范围：`pkg/scheduler/**`、`cmd/kube-scheduler/**`、`staging/k8s.io/kube-scheduler/**`，**包含测试文件**。

| 目录 | 文件 | 行数 | 注释块 | 行尾注释 |
|---|---|---|---|---|
| `pkg/scheduler/**` | 158 | 79,074 | 3,667 | 131 |
| `cmd/kube-scheduler/**` | 10 | 2,975 | 115 | 21 |
| `staging/k8s.io/kube-scheduler/**` | 9 | 1,930 | 230 | 0 |
| **合计** | **177** | **83,979** | **4,012** | **152** |

其中测试文件 52 个。译文共 4,164 条映射 + 6 处块注释补丁。

因为「只追加、不增行」，**本文所有 `文件:行号` 在汉化后依然精确有效**，无需换算。

### 译文映射与一键恢复

译文不写进文档，存在 `scripts/annotations/`：

- `manifest.json`：177 个文件与映射文件的对应关系，及源码版本（v1.32.0）。
- `*.json`：`key` = 注释块最后一行或行尾注释所在行（1-based），`value` = 中文译文；只含译文，不含源码。
- `block_comments.json`：6 处 `/* ... */` 块注释的 old/new 补丁，由 `apply_block_comments.py` 应用。

重新拉源码后，一条命令恢复：

```bash
cd /c/Users/Wp_/go/src/scheduler
bash scripts/apply-annotations.sh                # 用 .agents/source-root.local
bash scripts/apply-annotations.sh --source-root ../kubernetes-v1.32.0
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts/apply-annotations.ps1
powershell -ExecutionPolicy Bypass -File scripts/apply-annotations.ps1 -SourceRoot D:\code\GoCode\src\scheduler\k8s-v1.32.0
```

脚本会跳过已含中文的文件，逐文件校验行数、代码（去注释后）一致性、注释覆盖和 `gofmt`，最后应用块注释补丁。

### 校验方式

```bash
cd /c/Users/Wp_/go/src/scheduler

gofmt -l pkg/scheduler cmd/kube-scheduler staging/k8s.io/kube-scheduler   # 无输出 = 格式合规
go build ./pkg/scheduler/... ./cmd/kube-scheduler/...                     # 通过
go test -run '^$' ./pkg/scheduler/... ./cmd/kube-scheduler/...            # 测试文件可编译

# 行数与代码（去注释后）不变
python scripts/apply_annotations.py --source-root .   # 已汉化时全部 SKIP
```

处理前的干净原件在 `.local-backup/clean/<相对路径>`，供回退。

格式约定：`// English original. // 中文译文`；译文挂在注释块最后一行；空注释行保持纯 `//`；许可头、`//go:build`、`//nolint` 不译。

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
