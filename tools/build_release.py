"""Build internal alpha wheel/sdist and separately installable Skill archive."""
import hashlib,json,subprocess,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];subprocess.run([sys.executable,'-m','build','--no-isolation'],cwd=root,check=True)
out=root/'dist';skill_zip=out/'easy-to-3d-structural-design-0.1.0a1.zip'
with zipfile.ZipFile(skill_zip,'w',zipfile.ZIP_DEFLATED) as archive:
    for p in (root/'skills/structural-design').rglob('*'):
        if p.is_file():archive.write(p,p.relative_to(root/'skills'))
manifest={'version':'0.1.0a1','kind':'local alpha; not public release','license':'Apache-2.0','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='checksums.json'}}
(out/'checksums.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
