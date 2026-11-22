#!/usr/bin/env python3
"""Apply the checked-in Chinese comment maps to a kube-scheduler source tree.

This is the "restore annotations after a fresh checkout" entry point. It reads
scripts/annotations/manifest.json, applies each map through annotate_comments.py,
verifies line counts / code (comments stripped) / coverage, applies the
/* ... */ block-comment patches, and checks gofmt.

Usage:
  python scripts/apply_annotations.py --source-root /path/to/kubernetes
  python scripts/apply_annotations.py --source-root . --only schedule_one.go

If --source-root is omitted, .agents/source-root.local is used.
"""

import argparse
import io
import json
import os
import re
import subprocess
import sys

CJK = re.compile(r'[\u4e00-\u9fff]')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def read_source_root(explicit):
    if explicit:
        return os.path.abspath(explicit)
    local = os.path.join(REPO, '.agents', 'source-root.local')
    if os.path.isfile(local):
        value = io.open(local, encoding='utf-8').read().strip()
        if value:
            return os.path.abspath(value)
    return REPO


def run(cmd):
    proc = subprocess.run(cmd, cwd=REPO, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True)
    return proc.returncode, proc.stdout.strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-root', default=None)
    p.add_argument('--only', default=None, help='仅处理路径中包含该子串的文件')
    args = p.parse_args()

    source_root = read_source_root(args.source_root)
    manifest_path = os.path.join(HERE, 'annotations', 'manifest.json')
    manifest = json.load(io.open(manifest_path, encoding='utf-8'))
    entries = manifest['files']
    if args.only:
        entries = [e for e in entries if args.only in e['file']]
        if not entries:
            raise SystemExit('no manifest entry matches %r' % args.only)

    print('source root: %s' % source_root)
    print('annotation version: %s' % manifest.get('version', '?'))
    failed = []
    applied = skipped = 0

    for entry in entries:
        rel = entry['file']
        target = os.path.join(source_root, rel)
        mapping = os.path.join(HERE, 'annotations', entry['map'])
        if not os.path.isfile(target):
            print('MISS  %s' % rel)
            failed.append(rel)
            continue

        text = io.open(target, encoding='utf-8').read()
        ref = os.path.join(REPO, '.local-backup', 'clean', rel)
        if not os.path.isfile(ref):
            ref = target

        if CJK.search(text):
            # 已有中文：仍然校验一遍，避免半套注释被静默跳过。
            code, out = run([sys.executable, os.path.join(HERE, 'annotate_comments.py'),
                             '--check', '--scope', 'all', target, '--ref', ref])
            if code != 0:
                print('FAIL  %s\n%s' % (rel, out))
                failed.append(rel)
                continue
            print('SKIP  %s（已有中文注释，校验通过）' % rel)
            skipped += 1
            continue

        # 优先用仓库里的干净原件做参考；新机器没有备份时，干净源码本身就是参考。

        code, out = run([sys.executable, os.path.join(HERE, 'annotate_comments.py'),
                         '--apply', target, '--ref', ref, '--map', mapping, '--in-place'])
        if code != 0:
            print('FAIL  %s\n%s' % (rel, out))
            failed.append(rel)
            continue

        code, out = run([sys.executable, os.path.join(HERE, 'annotate_comments.py'),
                         '--check', '--scope', 'all', target, '--ref', ref])
        if code != 0:
            print('FAIL  %s\n%s' % (rel, out))
            failed.append(rel)
            continue

        code, out = run(['gofmt', '-l', target])
        if code != 0 or out:
            print('FAIL  gofmt %s\n%s' % (rel, out))
            failed.append(rel)
            continue

        print('OK    %s  %s' % (rel, out))
        applied += 1

    code, out = run([sys.executable, os.path.join(HERE, 'apply_block_comments.py'),
                     '--source-root', source_root])
    if code != 0:
        print('FAIL  block comments\n%s' % out)
        failed.append('block_comments')
    else:
        print(out)

    print('\napplied %d, skipped %d, failed %d' % (applied, skipped, len(failed)))
    if failed:
        print('failed: %s' % ', '.join(failed))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
