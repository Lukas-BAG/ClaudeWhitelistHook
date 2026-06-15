# Hook instructions — file access whitelist

You may only access files that are explicitly listed in `.claude/whitelist.txt`.

The format uses `r:` for read-only and `w:` for write (write also grants read):
- `r: path` — you may read this file
- `w: path` — you may read and write this file

Before reading, editing, or writing any file, check whether it is whitelisted. If it is not, **do not access it**. Tell the user which file you need and ask them to add it to the whitelist first.

This applies to all file-accessing tools: `Read`, `Edit`, `Write`, and `Bash` commands that read or modify files. Do not reference non-whitelisted file paths in `Bash` commands either, even if the command itself is not blocked.

Note: this is a soft guardrail layered on top of Claude's own permission settings, not an airtight sandbox.

## Managing the whitelist

A script is provided to add, update, or remove entries. You cannot run it yourself — direct the user to run it with the `!` prefix:

```
! .claude/whitelist.sh read <path>    # grant read-only access
! .claude/whitelist.sh write <path>   # grant read+write access
! .claude/whitelist.sh none <path>    # revoke all access
```

Paths can be relative (resolved from the project root) or absolute. The script normalises paths automatically, handles upgrades and downgrades in place, and removes duplicates on each run.

When you need access to a file that is not whitelisted, tell the user which file and which permission level you need, and ask them to run the appropriate command above.

Source: https://github.com/Lukas-BAG/ClaudeWhitelistHook
