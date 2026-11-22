# 中文注释映射（kube-scheduler v1.32.0）

这些 JSON 只保存译文，不包含 Kubernetes 源码。覆盖 `pkg/scheduler/**`、`cmd/kube-scheduler/**`、`staging/k8s.io/kube-scheduler/**` 下**所有 Go 文件（含 `_test.go`）**：**177 个文件、83,979 行、4,012 个注释块 + 152 条行尾注释 + 6 处块注释**。

- `manifest.json`：177 个文件、对应映射文件、源码版本。
- `block_comments.json`：6 处 `/* ... */` 块注释补丁，由 `scripts/apply_block_comments.py` 应用。
- `*.json`：`key` 是注释块最后一行的 1-based 行号，`value` 是中文译文。
- 应用方式：在每个注释块最后一行的英文后面追加 ` // 中文译文`，不增删行、不改代码。

## 一键恢复

```bash
# 用 .agents/source-root.local 记录的源码根
bash scripts/apply-annotations.sh

# 指定源码根
bash scripts/apply-annotations.sh --source-root /path/to/kubernetes-v1.32.0
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts/apply-annotations.ps1 -SourceRoot D:\code\GoCode\src\scheduler\k8s-v1.32.0
```

脚本会逐文件执行：跳过已汉化文件 → 应用映射 → 校验行数/代码前缀/覆盖 → `gofmt -l`。

## 单文件流程

```bash
# 1. 列出注释块末行与行尾注释（生成空模板，填好译文）
python scripts/annotate_comments.py --list --scope all pkg/scheduler/scheduler.go > /tmp/map.json

# 2. 应用（把 /tmp/map.json 换成实际填写的文件）
python scripts/annotate_comments.py --apply pkg/scheduler/scheduler.go \
  --ref .local-backup/clean/pkg/scheduler/scheduler.go \
  --map /tmp/map.json --in-place

# 3. 校验
python scripts/annotate_comments.py --check --scope all pkg/scheduler/scheduler.go \
  --ref .local-backup/clean/pkg/scheduler/scheduler.go
```

## 注意

- 行号绑定 **v1.32.0**。换版本后必须重新生成映射，否则 `--check` 会报代码前缀不一致。
- 不要手工在 JSON 里塞换行；一条译文对应一个注释块。
- 许可头、`//go:build`、`//nolint`、纯 `//` 空行不翻译。
