#!/usr/bin/env bash
# 拉取 kube-scheduler v1.32.0 源码（tag tarball，约 40MB，不含 .git）
set -euo pipefail

VERSION="v1.32.0"
DEST="${1:-kubernetes-${VERSION}}"

if [ -f "$DEST/pkg/scheduler/schedule_one.go" ]; then
    echo "source already present: $DEST"
    exit 0
fi

mkdir -p "$DEST"
URL="https://github.com/kubernetes/kubernetes/archive/refs/tags/${VERSION}.tar.gz"

echo "downloading ${URL}"
curl -fL "$URL" | tar -xz --strip-components=1 -C "$DEST"

if [ ! -f "$DEST/pkg/scheduler/schedule_one.go" ]; then
    echo "unexpected layout: $DEST/pkg/scheduler/schedule_one.go not found" >&2
    exit 1
fi

echo "done: $DEST"
echo "verify: sed -n '65p' \"$DEST/pkg/scheduler/schedule_one.go\""
