#!/usr/bin/env python3
"""
install.py — add the PreToolUse whitelist hook to an existing Claude Code project.

This does not install software. It writes a hook script and config files into
an existing project's .claude/ directory and wires them up. Everything written
to disk is embedded in this file as plain text — no network calls, no surprises.

Usage:
    python3 install.py /path/to/your/project
    python3 install.py .
"""
import argparse
import os
import sys

CLAUDE_MD_IMPORT = "@.claude/hook_instructions.md"

# ── files written to the target project ──────────────────────────────────────

HOOK_SCRIPT = """\
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

if os.path.realpath(CLAUDE_DIR) == os.path.realpath(os.path.expanduser("~/.claude")):
    print(
        "Error: this hook must be configured per-project in .claude/settings.json, "
        "not globally in ~/.claude/settings.json. "
        "Path resolution relies on the hook's location to find the project root and whitelist. "
        "See the README for setup instructions.",
        file=sys.stderr,
    )
    sys.exit(2)

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
"""

HOOK_INSTRUCTIONS = """\
# Hook instructions — file access whitelist

You may only access files that are explicitly listed in `.claude/whitelist.txt`.

The format uses `r:` for read-only and `w:` for write (write also grants read):
- `r: path` — you may read this file
- `w: path` — you may read and write this file

Before reading, editing, or writing any file, check whether it is whitelisted. If it is not, **do not access it**. Tell the user which file you need and ask them to add it to the whitelist first.

This applies to all file-accessing tools: `Read`, `Edit`, `Write`, and `Bash` commands that read or modify files. Do not reference non-whitelisted file paths in `Bash` commands either, even if the command itself is not blocked.

Note: this is a soft guardrail layered on top of Claude's own permission settings, not an airtight sandbox.

Source: https://github.com/Lukas-BAG/ClaudeWhitelistHook
"""

FRESH_WHITELIST = """\
# Whitelist for Claude file access.
# This file itself is intentionally NOT listed here.
#
# Format:
#   r: path   read-only access
#   w: path   write access (implicitly grants read too)
#
# Paths can be absolute or relative to the project root.
# Inline comments after ' #' are stripped.

r: .claude/whitelist.txt
r: .claude/hook_instructions.md
r: .claude/settings.json
"""

SETTINGS_SNIPPET = """\
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Edit|Write|Bash",
        "hooks": [{ "type": "command", "command": "python3 .claude/hooks/pre_tool_use.py" }]
      }
    ]
  }
}
"""

# ── installer ─────────────────────────────────────────────────────────────────

def write_if_absent(path, content, label):
    if os.path.exists(path):
        print(f"  [skip]    {label} — already exists")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(content)
    print(f"  [created] {label}")


def install(target_dir):
    target_dir = os.path.realpath(target_dir)
    if not os.path.isdir(target_dir):
        sys.exit(f"Error: target directory does not exist: {target_dir}")

    dst = os.path.join(target_dir, ".claude")
    print(f"\nTarget: {target_dir}\n")

    write_if_absent(os.path.join(dst, "hooks/pre_tool_use.py"), HOOK_SCRIPT, ".claude/hooks/pre_tool_use.py")
    write_if_absent(os.path.join(dst, "hook_instructions.md"), HOOK_INSTRUCTIONS, ".claude/hook_instructions.md")
    write_if_absent(os.path.join(dst, "whitelist.txt"), FRESH_WHITELIST, ".claude/whitelist.txt — edit to add your files")

    claude_md = os.path.join(target_dir, "CLAUDE.md")
    if os.path.exists(claude_md):
        content = open(claude_md).read()
        if CLAUDE_MD_IMPORT in content:
            print(f"  [skip]    CLAUDE.md — import line already present")
        else:
            with open(claude_md, "a") as f:
                if not content.endswith("\n"):
                    f.write("\n")
                f.write(f"\n{CLAUDE_MD_IMPORT}\n")
            print(f"  [updated] CLAUDE.md — appended import line")
    else:
        open(claude_md, "w").write(f"{CLAUDE_MD_IMPORT}\n")
        print(f"  [created] CLAUDE.md")

    settings = os.path.join(dst, "settings.json")
    if os.path.exists(settings):
        print(f"\n  [manual]  .claude/settings.json already exists — merge this in:\n")
        print(SETTINGS_SNIPPET)
    else:
        write_if_absent(settings, SETTINGS_SNIPPET, ".claude/settings.json")

    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", nargs="?", default=os.getcwd(), help="Target project directory (default: cwd)")
    install(parser.parse_args().target)
