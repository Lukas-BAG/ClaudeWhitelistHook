#!/usr/bin/env python3
"""
install.py — add the PreToolUse whitelist hook config to an existing project.

This does not install software. It copies a hook script and config files into
an existing project's .claude/ directory and wires them up.

Local (run from within the cloned repo):
    python3 install.py /path/to/your/project
    python3 install.py .                        # current directory

From git (no clone needed):
    curl -fsSL https://raw.githubusercontent.com/Lukas-BAG/ClaudeWhitelistHook/main/install.py \\
      | python3 - --from-git https://github.com/Lukas-BAG/ClaudeWhitelistHook /path/to/your/project
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HOOK_SCRIPT_REL      = "hooks/pre_tool_use.py"
HOOK_INSTRUCTIONS_REL = "hook_instructions.md"
WHITELIST_REL        = "whitelist.txt"
CLAUDE_MD_IMPORT     = "@.claude/hook_instructions.md"

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

r: .claude/hook_instructions.md  # read-only: Claude can read its instructions but not modify them
"""

SETTINGS_HOOK_SNIPPET = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Read|Edit|Write|Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 .claude/hooks/pre_tool_use.py"
                    }
                ]
            }
        ]
    }
}


def copy_if_absent(src, dst, label):
    if os.path.exists(dst):
        print(f"  [skip]    {label} — already exists, not overwritten")
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  [created] {label}")


def install(source_claude_dir, target_dir):
    target_dir = os.path.realpath(target_dir)
    if not os.path.isdir(target_dir):
        sys.exit(f"Error: target directory does not exist: {target_dir}")

    print(f"\nInstalling into: {target_dir}\n")
    target_claude_dir = os.path.join(target_dir, ".claude")

    # Hook script
    copy_if_absent(
        os.path.join(source_claude_dir, HOOK_SCRIPT_REL),
        os.path.join(target_claude_dir, HOOK_SCRIPT_REL),
        ".claude/hooks/pre_tool_use.py",
    )

    # Hook instructions
    copy_if_absent(
        os.path.join(source_claude_dir, HOOK_INSTRUCTIONS_REL),
        os.path.join(target_claude_dir, HOOK_INSTRUCTIONS_REL),
        ".claude/hook_instructions.md",
    )

    # Whitelist — always a fresh template, never overwrite an existing one
    whitelist_dst = os.path.join(target_claude_dir, WHITELIST_REL)
    if os.path.exists(whitelist_dst):
        print(f"  [skip]    .claude/whitelist.txt — already exists, not overwritten")
    else:
        os.makedirs(target_claude_dir, exist_ok=True)
        with open(whitelist_dst, "w") as f:
            f.write(FRESH_WHITELIST)
        print(f"  [created] .claude/whitelist.txt  (template — edit to add your files)")

    # CLAUDE.md — append import line if not already present
    claude_md_path = os.path.join(target_dir, "CLAUDE.md")
    if os.path.exists(claude_md_path):
        content = open(claude_md_path).read()
        if CLAUDE_MD_IMPORT in content:
            print(f"  [skip]    CLAUDE.md — import line already present")
        else:
            with open(claude_md_path, "a") as f:
                if not content.endswith("\n"):
                    f.write("\n")
                f.write(f"\n{CLAUDE_MD_IMPORT}\n")
            print(f"  [updated] CLAUDE.md — appended import line")
    else:
        with open(claude_md_path, "w") as f:
            f.write(f"{CLAUDE_MD_IMPORT}\n")
        print(f"  [created] CLAUDE.md")

    # settings.json — create if absent, otherwise show manual instructions
    settings_path = os.path.join(target_claude_dir, "settings.json")
    if os.path.exists(settings_path):
        snippet = json.dumps(SETTINGS_HOOK_SNIPPET, indent=2)
        print(f"\n  [manual]  .claude/settings.json already exists.")
        print( "            Merge the following into it under the top-level \"hooks\" key:\n")
        for line in snippet.splitlines():
            print(f"            {line}")
    else:
        os.makedirs(target_claude_dir, exist_ok=True)
        with open(settings_path, "w") as f:
            json.dump(SETTINGS_HOOK_SNIPPET, f, indent=2)
            f.write("\n")
        print(f"  [created] .claude/settings.json")

    print("\nDone.")


def install_from_git(repo_url, target_dir):
    with tempfile.TemporaryDirectory() as tmp:
        print(f"Cloning {repo_url} ...")
        subprocess.run(["git", "clone", "--depth", "1", repo_url, tmp], check=True)
        source_claude_dir = os.path.join(tmp, ".claude")
        if not os.path.isdir(source_claude_dir):
            sys.exit("Error: expected .claude/ directory in the repository root")
        install(source_claude_dir, target_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Install the PreToolUse whitelist hook into a target project."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=os.getcwd(),
        help="Target project directory (default: current directory)",
    )
    parser.add_argument(
        "--from-git",
        metavar="URL",
        help="Clone the hook tool from this git URL instead of using local files",
    )
    args = parser.parse_args()

    if args.from_git:
        install_from_git(args.from_git, args.target)
    else:
        script_file = os.path.realpath(__file__)
        if not os.path.isfile(script_file):
            sys.exit("Error: cannot locate source files when running from stdin. Use --from-git URL instead.")
        local_claude_dir = os.path.join(os.path.dirname(script_file), ".claude")
        install(local_claude_dir, args.target)
