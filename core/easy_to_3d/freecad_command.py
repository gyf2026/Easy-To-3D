"""Keep Unicode workspace paths out of Windows FreeCAD's script argv.

The user's script and working directory remain unchanged. A per-run ASCII
relative entry point lets embedded Python read the original Unicode path.
"""
import json
import os
from pathlib import Path, PureWindowsPath
from .storage import digest


def prepare(root, command, archive, windows=None):
    command=list(command)
    if windows is None:windows=os.name=='nt'
    if not windows or PureWindowsPath(command[0]).name.lower() not in ('freecadcmd','freecadcmd.exe'):
        return command,None
    for index,argument in enumerate(command[1:],1):
        if not argument.lower().endswith('.py') or argument.isascii():continue
        script=Path(argument)
        if not script.is_absolute():script=Path(root)/script
        script=script.resolve()
        if not script.is_file():continue # Preserve ordinary backend failure diagnostics.
        entry=Path(archive)/'freecad_entry.py'
        # ensure_ascii makes even the wrapper's source safe for older loaders.
        payload=json.dumps({'script':str(script),'args':command[index+1:]},ensure_ascii=True)
        source=("import sys, runpy, json\n"
                f"_payload = json.loads({ascii(payload)})\n"
                "_script = _payload['script']\n"
                "sys.argv = [_script] + _payload['args']\n"
                "from pathlib import Path\n"
                "sys.path.insert(0, str(Path(_script).parent))\n"
                "runpy.run_path(_script, run_name='__main__')\n")
        entry.write_text(source,encoding='ascii')
        relative=entry.relative_to(Path(root)).as_posix()
        # Script arguments are reconstructed inside Python, so their Unicode
        # text never passes through FreeCAD's native command-line parser.
        command[index:]=[relative]
        return command,{'kind':'windows-freecad-unicode-script','source':str(script),'source_sha256':digest(script),'entry':relative,'entry_sha256':digest(entry)}
    return command,None
