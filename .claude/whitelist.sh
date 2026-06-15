#!/usr/bin/env python3
'''Manage .claude/whitelist.txt entries. Usage: whitelist.sh read|write|none <path>'''

import os
import re
import sys
from pathlib import Path


def normalize(path_str, project_root):
    p = Path(path_str)
    if not p.is_absolute():
        p = Path.cwd() / p
    abs_p = Path(os.path.normpath(str(p)))
    try:
        return str(abs_p.relative_to(project_root))
    except ValueError:
        return str(abs_p)


def parse_entry(line):
    stripped = re.sub(r'\s+#.*$', '', line).rstrip()
    m = re.match(r'^\s*(r|w):\s+(.+)', stripped)
    return (m.group(1), m.group(2)) if m else None


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('read', 'write', 'none'):
        print(f"Usage: {os.path.basename(sys.argv[0])} read|write|none <path>", file=sys.stderr)
        sys.exit(1)

    new_perm = {'read': 'r', 'write': 'w', 'none': None}[sys.argv[1]]
    input_path = sys.argv[2]

    script_dir = Path(os.path.realpath(__file__)).parent
    project_root = script_dir.parent
    whitelist_path = script_dir / 'whitelist.txt'

    if os.path.realpath(os.getcwd()) != str(project_root):
        print(f"Error: must be run from the project root.", file=sys.stderr)
        print(f"  expected: {project_root}", file=sys.stderr)
        print(f"  current:  {os.getcwd()}", file=sys.stderr)
        sys.exit(1)

    if not whitelist_path.exists():
        whitelist_path.touch()
        print(f"Created: {whitelist_path}")

    p_abs = os.path.normpath(os.path.abspath(input_path))
    if os.path.realpath(p_abs) != p_abs:
        print(f"Error: '{input_path}' involves a symlink — use the real path instead.", file=sys.stderr)
        sys.exit(1)

    target = normalize(input_path, project_root)

    with open(whitelist_path) as f:
        lines = f.readlines()

    by_norm = {}
    for i, line in enumerate(lines):
        parsed = parse_entry(line)
        if parsed:
            perm, raw = parsed
            norm = normalize(raw, project_root)
            by_norm.setdefault(norm, []).append((i, perm))

    target_entries = by_norm.get(target, [])
    existing_perm = ('w' if any(p == 'w' for _, p in target_entries) else 'r') if target_entries else None

    lines_to_remove = set()
    lines_to_replace = {}
    duplicate_count = 0

    for norm, entries in by_norm.items():
        if norm == target or len(entries) <= 1:
            continue
        best = 'w' if any(p == 'w' for _, p in entries) else 'r'
        kept = False
        for idx, perm in entries:
            if not kept and perm == best:
                kept = True
            else:
                lines_to_remove.add(idx)
                duplicate_count += 1

    append_new = False
    if target_entries:
        if new_perm is None:
            for idx, _ in target_entries:
                lines_to_remove.add(idx)
        else:
            first_idx = target_entries[0][0]
            lines_to_replace[first_idx] = f'{new_perm}: {target}\n'
            for idx, _ in target_entries[1:]:
                lines_to_remove.add(idx)
    elif new_perm is not None:
        append_new = True

    new_lines = []
    for i, line in enumerate(lines):
        if i in lines_to_remove:
            continue
        new_lines.append(lines_to_replace.get(i, line))

    if append_new:
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
        new_lines.append(f'{new_perm}: {target}\n')

    with open(whitelist_path, 'w') as f:
        f.writelines(new_lines)

    perm_name = {'r': 'read', 'w': 'write', None: 'none'}
    if new_perm is None and existing_perm is None:
        print(f"No change:  '{target}' was not in the whitelist.")
    elif new_perm is None:
        print(f"Removed:    '{target}'  ({perm_name[existing_perm]} access revoked).")
    elif existing_perm is None:
        print(f"Added:      {new_perm}: {target}")
    elif existing_perm == new_perm:
        print(f"No change:  '{target}' already has {perm_name[new_perm]} access.")
    elif new_perm == 'w':
        print(f"Upgraded:   '{target}'  (read → write).")
    else:
        print(f"Downgraded: '{target}'  (write → read).")

    if duplicate_count:
        print(f"Cleaned up {duplicate_count} duplicate entr{'y' if duplicate_count == 1 else 'ies'}.")


if __name__ == '__main__':
    main()
