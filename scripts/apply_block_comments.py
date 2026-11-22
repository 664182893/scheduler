#!/usr/bin/env python3
"""Apply the block-comment translations that cannot be expressed as line maps.

Some English comments are inside /* ... */ on a code line. Appending // would
comment out the rest of the line, so these are stored as old/new patches in
scripts/annotations/block_comments.json.
"""

import argparse
import io
import json
import os
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def write_lines(path, lines):
    data = '\n'.join(lines)
    mode = os.stat(path).st_mode
    try:
        with io.open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(data)
    except PermissionError:
        os.chmod(path, mode | stat.S_IWRITE)
        try:
            with io.open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(data)
        finally:
            os.chmod(path, mode)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-root', default=REPO)
    args = p.parse_args()
    root = os.path.abspath(args.source_root)
    data = json.load(io.open(os.path.join(HERE, 'annotations', 'block_comments.json'), encoding='utf-8'))

    changed = already = 0
    for patch in data['patches']:
        path = os.path.join(root, patch['file'])
        lines = io.open(path, encoding='utf-8', newline='').read().split('\n')
        idx = patch['line'] - 1
        line = lines[idx]
        if patch['new'] in line:
            already += 1
            continue
        if patch['old'] not in line:
            raise SystemExit('patch target not found: %s:%d' % (patch['file'], patch['line']))
        lines[idx] = line.replace(patch['old'], patch['new'], 1)
        write_lines(path, lines)
        changed += 1
        print('patched %s:%d' % (patch['file'], patch['line']))

    print('block comments: patched %d, already %d' % (changed, already))
    return 0


if __name__ == '__main__':
    sys.exit(main())
