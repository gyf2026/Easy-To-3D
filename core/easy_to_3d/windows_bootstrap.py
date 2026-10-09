"""Windows job handshake: the backend cannot spawn before its launcher joins the job."""
import json
import subprocess
import sys

if __name__ == '__main__':
    if sys.stdin.buffer.read(1) != b'1': raise SystemExit(125)
    child=subprocess.Popen(json.loads(sys.argv[1]),stdin=subprocess.DEVNULL)
    raise SystemExit(child.wait())
