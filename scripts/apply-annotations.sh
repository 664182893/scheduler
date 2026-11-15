#!/usr/bin/env bash
# 把 scripts/annotations/ 里的中文注释映射应用到源码树。
# 用法: bash scripts/apply-annotations.sh [--source-root DIR] [--only SUBSTR]
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python "$repo/scripts/apply_annotations.py" "$@"
