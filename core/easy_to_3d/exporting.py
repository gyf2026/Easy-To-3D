import shutil
import tempfile
import os
from pathlib import Path
from .storage import digest, atomic, confined, now
from .contracts import require
from .mesh import project_triangles, write_stl, read_stl
from .checks import mesh_facts

def _export(project,ident,profile,output):
    version=project.version(ident); root=project.version_root(ident)
    require(project.verify(ident)['artifacts']['status']=='pass','Published artifacts changed; cannot export')
    output=Path(output); files=[]
    if profile=='print':
        triangles=project_triangles(confined(root,version['artifacts']['preview']),version['artifacts']['preview_to_project'])
        name=ident+'.stl'; require(not (output/name).exists(),'Export already exists; choose a new directory')
        write_stl(output/name,triangles); measured=mesh_facts(read_stl(output/name)); original=mesh_facts(triangles)
        require(all(abs(a-b)<=.01 for a,b in zip(measured['size_mm'],original['size_mm'])),'STL round-trip dimensions differ')
        (output/'打印说明.md').write_text('# 打印文件说明\n\n版本：'+ident+'\n\nSTL 坐标单位为毫米（mm），请在切片器中按毫米导入。\n尺寸：'+str(measured['size_mm'])+' mm。\n\n导出成功不代表打印适用性已经验证。壁厚、间隙、材料、支撑、摆放方向需按工艺确认；本程序不生成 G-code。\n',encoding='utf-8')
        files=[name,'打印说明.md']; unresolved=['wall_thickness','clearance','supports','orientation','material']
        checks={'mesh':measured,'status':'fail' if any(measured[x] for x in ('boundary_edges','nonmanifold_edges','inconsistent_winding_edges','degenerate_faces')) or measured['signed_volume_mm3']<=0 else 'unknown','unresolved':unresolved}
        atomic(output/'print-checks.json',checks); files.append('print-checks.json')
    else:
        drawing_files=[x for x in version['files'] if x.startswith('drawings/') and Path(x).suffix in ('.svg','.pdf')]
        require(bool(drawing_files),'No published drawings available')
        for relative in drawing_files:
            target=output/Path(relative).name; require(not target.exists(),'Output file already exists'); shutil.copy2(confined(root,relative),target); files.append(target.name)
    manifest={'schema_version':'1.0','project_id':project.data['id'],'model_version_id':ident,'profile':profile,'created_at':now(),'units':'mm','files':{x:digest(output/x) for x in files},'source_preview_hash':version['files'][version['artifacts']['preview']],'export_success':True,'suitability':checks['status'] if profile=='print' else 'unknown'}
    atomic(output/'manifest.json',manifest);return manifest


def export(project, ident, profile, output):
    """Commit one complete delivery; never overwrite model history or prior deliveries."""
    require(profile in ('print', 'drawings'), 'Unknown export profile')
    output = Path(output).expanduser().resolve()
    protected = [project.root / name for name in ('variants', 'workspace', 'requirements', 'references', '.cache')]
    require(output != project.root and not any(output.is_relative_to(p.resolve()) or p.resolve().is_relative_to(output) for p in protected), 'Export to a separate delivery directory outside project source/history')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Serialize exports targeting the same parent, including different versions.
    from .storage import lock
    with lock(output.parent):
        require(not output.exists() or (output.is_dir() and not any(output.iterdir())), 'Delivery directory must be new or empty; prior deliveries cannot be overwritten')
        stage = Path(tempfile.mkdtemp(prefix='.delivery-', dir=output.parent))
        try:
            manifest = _export(project, ident, profile, stage)
            # An externally changed source must not be committed as a verified export.
            require(project.verify(ident)['artifacts']['status'] == 'pass', 'Published artifacts changed during export')
            for file in stage.iterdir():
                if file.is_file():
                    with file.open('rb+') as stream:os.fsync(stream.fileno())
            if output.exists(): output.rmdir()
            os.replace(stage, output)
            return manifest
        finally:
            if stage.exists(): shutil.rmtree(stage)
