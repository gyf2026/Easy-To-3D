"""How this runtime is invoked, for argv arrays handed back to the user.

Deliverables, setup guidance and handoffs return argv arrays so an Agent can run
them without shell interpolation. The first element must match how this runtime
was actually started: an installed console script answers to `easy-to-3d`, a
Skill bundle answers to `python3 <skill>/scripts/et3d.py`, and a source checkout
answered to `python3 -m easy_to_3d`. Hard-coding one of them made the others emit
a command that does not exist on that machine.
"""
import os
import sys


def cli_argv():
    """Prefix for any command this runtime hands back, e.g. ['easy-to-3d']."""
    argv0 = (sys.argv[0] if sys.argv else '') or ''
    name = os.path.basename(argv0)
    if name in ('easy-to-3d', 'easy-to-3d.exe'):
        return ['easy-to-3d']
    if name == '__main__.py' or name in ('', '-c', '-m'):
        return [sys.executable, '-m', 'easy_to_3d']
    if name.endswith('.py'):
        return [sys.executable, argv0]
    return [argv0]
