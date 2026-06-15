#!/usr/bin/env python3
"""Regenerate the embedded content in install.py from the source files.

Run this whenever pre_tool_use.py or hook_instructions.md changes.
"""
import os

HERE = os.path.dirname(os.path.realpath(__file__))


def read(rel):
    return open(os.path.join(HERE, rel)).read()


def replace_block(source, varname, new_content, escape_backslashes=False):
    start_marker = f'{varname} = """\\\n'
    end_marker = '\n"""'
    start = source.index(start_marker) + len(start_marker)
    end = source.index(end_marker, start)
    content = new_content.rstrip('\n')
    if escape_backslashes:
        content = content.replace('\\', '\\\\')
    return source[:start] + content + source[end:]


install_py = read("install.py")
install_py = replace_block(install_py, "HOOK_SCRIPT", read(".claude/hooks/pre_tool_use.py"))
install_py = replace_block(install_py, "HOOK_INSTRUCTIONS", read(".claude/hook_instructions.md"))
install_py = replace_block(install_py, "WHITELIST_SCRIPT", read(".claude/whitelist.sh"), escape_backslashes=True)

open(os.path.join(HERE, "install.py"), "w").write(install_py)
print("install.py updated.")
