#!/usr/bin/env python3
"""Add Chinese translations to Go line comments without changing line numbers.

The translation is appended to the end of an existing comment line:

    // English original. // 中文译文

Every mode compares against a clean reference file and refuses to change code.

Usage:
  # 1. List the last line of every comment block (fill in the values)
  python scripts/annotate_comments.py --list pkg/scheduler/scheduler.go > map.json

  # 2. Apply translations in place
  python scripts/annotate_comments.py --apply pkg/scheduler/scheduler.go \
      --ref .local-backup/clean/pkg/scheduler/scheduler.go \
      --map scripts/annotations/pkg__scheduler__scheduler.go.json --in-place

  # 3. Verify line count, code prefix and translation coverage
  python scripts/annotate_comments.py --check pkg/scheduler/scheduler.go \
      --ref .local-backup/clean/pkg/scheduler/scheduler.go

  # 4. Extract an existing annotated file back into a map
  python scripts/annotate_comments.py --extract pkg/scheduler/scheduler.go \
      --ref .local-backup/clean/pkg/scheduler/scheduler.go \
      --out scripts/annotations/pkg__scheduler__scheduler.go.json
"""

import argparse
import io
import json
import re
import sys

CJK = re.compile(r'[\u4e00-\u9fff]')
SKIP_PREFIXES = (
    '//go:',
    '// +build',
    '// Code generated',
    '//nolint',
)
SKIP_EXACT = ('//',)


def read_lines(path):
    return io.open(path, encoding='utf-8', newline='').read().split('\n')


def write_lines(path, lines):
    with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))


def is_comment(line):
    return line.lstrip().startswith('//')


def is_skippable(line):
    s = line.strip()
    return s in SKIP_EXACT or s.startswith(SKIP_PREFIXES)


def comment_blocks(lines):
    """Yield (start, end) 1-based inclusive for meaningful // comment blocks."""
    i = 0
    while i < len(lines):
        if is_comment(lines[i]):
            start = i
            while i < len(lines) and is_comment(lines[i]):
                i += 1
            end = i - 1
            block = lines[start:i]
            if any(not is_skippable(x) for x in block):
                yield start + 1, end + 1
        else:
            i += 1


def cmd_list(args):
    lines = read_lines(args.file)
    mapping = {str(end): '' for _, end in comment_blocks(lines)}
    print(json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=False))
    return 0


def load_map(path):
    data = json.load(io.open(path, encoding='utf-8'))
    out = {}
    for k, v in data.items():
        v = (v or '').strip()
        if not v:
            continue
        if '\n' in v:
            raise SystemExit('translation for line %s contains a newline' % k)
        out[int(k)] = v
    return out


def cmd_apply(args):
    lines = read_lines(args.file)
    ref = read_lines(args.ref)
    if len(lines) != len(ref):
        raise SystemExit('line count differs from ref: %d vs %d' % (len(lines), len(ref)))
    mapping = load_map(args.map)

    for lineno, text in mapping.items():
        if lineno < 1 or lineno > len(lines):
            raise SystemExit('line %d out of range' % lineno)
        line = lines[lineno - 1]
        ref_line = ref[lineno - 1]
        if line != ref_line:
            raise SystemExit('line %d is not clean; apply to a clean file first' % lineno)
        if '//' not in line:
            raise SystemExit('line %d has no comment to append to' % lineno)
        lines[lineno - 1] = line.rstrip() + ' // ' + text

    if args.in_place:
        write_lines(args.file, lines)
    else:
        sys.stdout.write('\n'.join(lines))
    return 0


def cmd_check(args):
    lines = read_lines(args.file)
    ref = read_lines(args.ref)
    problems = []

    if len(lines) != len(ref):
        problems.append('line count %d != ref %d' % (len(lines), len(ref)))
    else:
        for i, (a, b) in enumerate(zip(lines, ref), 1):
            if not a.startswith(b):
                problems.append('code changed at line %d: %r' % (i, a))
                if len(problems) > 10:
                    break

    missing = [
        (s, e) for s, e in comment_blocks(ref)
        if not any(CJK.search(lines[i - 1]) for i in range(s, e + 1))
    ]
    if missing:
        problems.append('untranslated comment blocks: %s' % ', '.join(
            '%d-%d' % m for m in missing))

    if problems:
        print('\n'.join(problems))
        return 1
    print('ok: %d lines, all comment blocks translated' % len(lines))
    return 0


def cmd_extract(args):
    lines = read_lines(args.file)
    ref = read_lines(args.ref)
    if len(lines) != len(ref):
        raise SystemExit('line count differs from ref: %d vs %d' % (len(lines), len(ref)))
    mapping = {}
    for i, (a, b) in enumerate(zip(lines, ref), 1):
        if a == b:
            continue
        if not a.startswith(b):
            raise SystemExit('code changed at line %d' % i)
        suffix = a[len(b):].strip()
        if suffix.startswith('//'):
            suffix = suffix[2:].strip()
        if CJK.search(suffix):
            mapping[str(i)] = suffix
    text = json.dumps(mapping, ensure_ascii=False, indent=2)
    io.open(args.out, 'w', encoding='utf-8', newline='\n').write(text + '\n')
    print('wrote %s (%d entries)' % (args.out, len(mapping)))
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('file')
    p.add_argument('--ref')
    p.add_argument('--map')
    p.add_argument('--out')
    p.add_argument('--in-place', action='store_true')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--list', action='store_true')
    g.add_argument('--apply', action='store_true')
    g.add_argument('--check', action='store_true')
    g.add_argument('--extract', action='store_true')
    args = p.parse_args()

    if args.list:
        return cmd_list(args)
    if not args.ref:
        raise SystemExit('--ref is required for this mode')
    if args.apply:
        if not args.map:
            raise SystemExit('--map is required for --apply')
        return cmd_apply(args)
    if args.check:
        return cmd_check(args)
    if args.extract:
        if not args.out:
            raise SystemExit('--out is required for --extract')
        return cmd_extract(args)


if __name__ == '__main__':
    sys.exit(main())
