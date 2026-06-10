#!/usr/bin/env python3
"""
install.py — add the PreToolUse whitelist hook to an existing Claude Code project.

This does not install software. It copies a hook script and config files into
an existing project's .claude/ directory and wires them up.

Local (run from within the cloned repo):
    python3 install.py /path/to/your/project
    python3 install.py .

From git (no clone needed):
    curl -fsSL https://raw.githubusercontent.com/Lukas-BAG/ClaudeWhitelistHook/main/install.py \
      | python3 - --from-git https://github.com/Lukas-BAG/ClaudeWhitelistHook /path/to/your/project
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

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

    print(f"\nTarget: {target_dir}\n")
    dst = os.path.join(target_dir, ".claude")

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


def install_from_git(repo_url, target_dir):
    with tempfile.TemporaryDirectory() as tmp:
        print(f"Cloning {repo_url} ...")
        subprocess.run(["git", "clone", "--depth", "1", repo_url, tmp], check=True)
        source = os.path.join(tmp, ".claude")
        if not os.path.isdir(source):
            sys.exit("Error: expected .claude/ directory at the repository root")
        install(source, target_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", nargs="?", default=os.getcwd(), help="Target project directory (default: cwd)")
    parser.add_argument("--from-git", metavar="URL", help="Clone from this URL instead of using local files")
    args = parser.parse_args()

    if args.from_git:
        install_from_git(args.from_git, args.target)
    else:
        script_file = os.path.realpath(__file__)
        if not os.path.isfile(script_file):
            sys.exit("Error: cannot locate source files from stdin — use --from-git URL instead")
        install(os.path.join(os.path.dirname(script_file), ".claude"), args.target)
