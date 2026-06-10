#!/usr/bin/env python3
# PreToolUse hook — file-access whitelist enforcement.
# This is an ADDITION to Claude's default permission rules, not a replacement.
# Claude's own settings (allow/deny/ask in settings.json) still apply independently.
# This hook adds a second layer: Read/Edit/Write are checked against whitelist.txt;
# any access to an unlisted file is blocked (exit 2).
#
# whitelist.txt format:
#   r: path/to/file   # read-only
#   w: path/to/file   # write (implicitly grants read too)
# Paths can be absolute or relative to the project root.
# Lines starting with # are comments. Inline comments after ' #' are also stripped.
import json
import os
import re
import sys

HOOK_DIR = os.path.dirname(os.path.realpath(__file__))
CLAUDE_DIR = os.path.realpath(os.path.join(HOOK_DIR, ".."))
PROJECT_ROOT = os.path.dirname(CLAUDE_DIR)
WHITELIST_PATH = os.path.join(CLAUDE_DIR, "whitelist.txt")

BLOCKED_BASH_COMMANDS = {
    "curl", "wget", "nc", "netcat", "ssh", "scp", "rsync",
    "cat", "python3", "python", "node", "perl", "ruby",
    "awk", "sed", "tee", "dd", "less", "more", "strings", "xxd",
}


def deny(reason):
    print(reason, file=sys.stderr)
    sys.exit(2)


def warn(msg):
    print(f"Warning: {msg}", file=sys.stderr)


def resolve(path):
    if os.path.isabs(path):
        return os.path.realpath(path)
    return os.path.realpath(os.path.join(PROJECT_ROOT, path))


def load_whitelist():
    read_paths = set()
    write_paths = set()
    try:
        with open(WHITELIST_PATH) as f:
            for lineno, raw in enumerate(f, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if not (line.startswith("r:") or line.startswith("w:")):
                    warn(f"whitelist.txt line {lineno}: unexpected format (expected 'r:' or 'w:') — ignored: {line!r}")
                    continue
                prefix = line[0]
                entry = line[2:].strip()
                # Strip inline comments
                if " #" in entry:
                    entry = entry[:entry.index(" #")].strip()
                if not entry:
                    warn(f"whitelist.txt line {lineno}: empty path after '{prefix}:' — ignored")
                    continue
                resolved = resolve(entry)
                if not os.path.exists(resolved):
                    warn(f"whitelist.txt line {lineno}: path does not exist: {resolved!r}")
                if prefix == "r":
                    read_paths.add(resolved)
                else:
                    write_paths.add(resolved)
    except FileNotFoundError:
        warn(f"whitelist file not found: {WHITELIST_PATH}")
    return read_paths, write_paths


try:
    data = json.load(sys.stdin)
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    cwd = data.get("cwd", "")

    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        resolved = os.path.realpath(os.path.join(cwd, file_path))
        read_paths, write_paths = load_whitelist()
        if resolved not in read_paths and resolved not in write_paths:
            deny(f"Blocked: '{file_path}' is not in the whitelist")

    elif tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path", "")
        resolved = os.path.realpath(os.path.join(cwd, file_path))
        _, write_paths = load_whitelist()
        if resolved not in write_paths:
            deny(f"Blocked: '{file_path}' is not in the write whitelist")

    elif tool_name == "Bash":
        command = tool_input.get("command", "").strip()
        parts = re.split(r'[|;&]+', command)
        for part in parts:
            words = part.strip().split()
            if words and words[0] in BLOCKED_BASH_COMMANDS:
                deny(f"Blocked: '{words[0]}' is not allowed")

except Exception as e:
    # Fail open — never block on hook errors
    print(f"Hook error (non-blocking): {e}", file=sys.stderr)

sys.exit(0)
