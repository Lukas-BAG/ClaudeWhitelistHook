# PreToolUse Hook — File Access Whitelist

Adds a `PreToolUse` hook to an existing Claude Code project that restricts which files Claude can read and write. This does not install any software — it copies a hook script and a few config files into your project's `.claude/` directory and wires them up.

It acts as an additional layer on top of Claude's own permission settings (`allow`/`deny`/`ask` in `settings.json`) — not a foolproof sandbox, but a clear soft guardrail.

## What's included

```
.claude/
  hooks/
    pre_tool_use.py     # the hook script
  whitelist.txt         # list of files Claude may access
  hook_instructions.md  # behavioral instructions loaded into Claude's context
```

## How to deploy

You need:
- `.claude/hooks/pre_tool_use.py` — the hook script
- `.claude/whitelist.txt` — the list of files Claude may access
- `.claude/settings.json` with a `PreToolUse` entry pointing to the hook script
- `CLAUDE.md` importing `.claude/hook_instructions.md` (optional but recommended)

### Option A — automatic install script

> **Read first!** The script copies files into your project and modifies `CLAUDE.md` and `settings.json`. Review what it does before running it, especially in an existing project.

Download `install.py` and run it pointing at your target project (`.` = current directory):

```bash
curl -fsSL https://raw.githubusercontent.com/Lukas-BAG/ClaudeWhitelistHook/main/install.py -o install.py
python3 install.py /path/to/your/project
```

`install.py` is self-contained — everything it writes to your project is embedded in the file as plain text. No network calls, no surprises. Read it before running.

The script will:
- Copy `pre_tool_use.py` and `hook_instructions.md` into `.claude/` (skips if already present)
- Create a fresh `whitelist.txt` template (skips if already present)
- Add `@.claude/hook_instructions.md` to `CLAUDE.md` (creates it if missing, appends if present)
- Create `settings.json` with the hooks block — or, if one already exists, print the snippet to add manually

After running, edit `.claude/whitelist.txt` to list the files Claude should be allowed to access.

### Option B — manual install

**1. Copy the `.claude/` directory into your project root**

```
your-project/
  .claude/
    hooks/
      pre_tool_use.py
    whitelist.txt
    hook_instructions.md
```

**2. Add the hook to your project's `.claude/settings.json`**

```json
{
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
```

**3. Add a reference to the hook instructions in your project's `CLAUDE.md`**

Add this line (create the file if it doesn't exist):

```
@.claude/hook_instructions.md
```

**4. Edit `whitelist.txt` to list the files Claude should be allowed to access**

```
r: path/to/file        # read-only
w: path/to/file        # write (implicitly grants read too)
```

Paths can be absolute or relative to the project root. Inline comments after ` #` are stripped.

## Notes

- The hook blocks `Read`, `Edit`, and `Write` calls to files not in the whitelist.
- Several Bash commands that read files are also blocked (`cat`, `sed`, `awk`, `python3`, etc.) — this is best-effort, not exhaustive.
- The hook fails open: if the script itself errors, it does not block the tool call.
- `whitelist.txt` is listed as read-only in itself — Claude can see what is whitelisted but cannot modify the list.

## Windows

The hook script itself is cross-platform. However, the command in `settings.json` uses `python3`, which is often not available on native Windows — the executable is typically just `python` there. If you're on Windows, change the command accordingly:

```json
"command": "python .claude/hooks/pre_tool_use.py"
```

On Linux and macOS, keep `python3` — `python` may not exist or may point to Python 2.
