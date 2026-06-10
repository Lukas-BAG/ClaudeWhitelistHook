#!/usr/bin/env python3
"""
install.py — add the PreToolUse whitelist hook to an existing Claude Code project.

This does not install software. It copies a hook script and config files into
an existing project's .claude/ directory and wires them up.

Usage:
    python3 install.py /path/to/your/project
    python3 install.py .

If run from outside the cloned repo, the required files are downloaded
automatically from GitHub.
"""
import argparse
import os
import shutil
import sys
import tempfile
import urllib.request

REPO_RAW = "https://raw.githubusercontent.com/Lukas-BAG/ClaudeWhitelistHook/main"
REMOTE_FILES = [
    ".claude/hooks/pre_tool_use.py",
    ".claude/hook_instructions.md",
]

CLAUDE_MD_IMPORT = "@.claude/hook_instructions.md"

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


def put(src, dst, label):
    if os.path.exists(dst):
        print(f"  [skip]    {label} — already exists")
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  [copied]  {label}")


def install(source_claude_dir, target_dir):
    target_dir = os.path.realpath(target_dir)
    if not os.path.isdir(target_dir):
        sys.exit(f"Error: target directory does not exist: {target_dir}")

    dst = os.path.join(target_dir, ".claude")
    print(f"\nTarget: {target_dir}\n")

    put(os.path.join(source_claude_dir, "hooks/pre_tool_use.py"), os.path.join(dst, "hooks/pre_tool_use.py"), ".claude/hooks/pre_tool_use.py")
    put(os.path.join(source_claude_dir, "hook_instructions.md"), os.path.join(dst, "hook_instructions.md"), ".claude/hook_instructions.md")

    whitelist = os.path.join(dst, "whitelist.txt")
    if os.path.exists(whitelist):
        print(f"  [skip]    .claude/whitelist.txt — already exists")
    else:
        os.makedirs(dst, exist_ok=True)
        open(whitelist, "w").write(FRESH_WHITELIST)
        print(f"  [created] .claude/whitelist.txt — edit to add your files")

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
        os.makedirs(dst, exist_ok=True)
        open(settings, "w").write(SETTINGS_SNIPPET)
        print(f"  [created] .claude/settings.json")

    print("Done.")


def fetch_source(tmp):
    print("Downloading files from GitHub...")
    src = os.path.join(tmp, ".claude")
    for rel in REMOTE_FILES:
        dst = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        urllib.request.urlretrieve(f"{REPO_RAW}/{rel}", dst)
        print(f"  {rel}")
    print()
    return src


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", nargs="?", default=os.getcwd(), help="Target project directory (default: cwd)")
    target = parser.parse_args().target

    local_claude = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".claude")
    if os.path.isdir(local_claude):
        install(local_claude, target)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            install(fetch_source(tmp), target)
