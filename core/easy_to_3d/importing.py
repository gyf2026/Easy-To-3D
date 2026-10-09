"""Explicit mesh import; original assets never execute and never gain CAD history."""
import shutil
import sys
from pathlib import Path
from .contracts import require, transform
from .storage import atomic, digest
from .mesh import read_glb, read_stl
from .glb import write_glb, PREVIEW_TO_PROJECT
from .checks import mesh_facts, check
from .execution import run

def source_matrix(units, up_axis):
    require(units in ('mm','cm','m'),'Explicit source units required')
    require(up_axis in ('Y','Z'),'Explicit source up axis required')
    scale={'mm':1,'cm':10,'m':1000}[units]
    if up_axis=='Z':return [scale,0,0,0,0,scale,0,0,0,0,scale,0,0,0,0,1]
    return [scale,0,0,0,0,0,-scale,0,0,scale,0,0,0,0,0,1]

def rebuild_mesh(root, source_name, units, up_axis):
    root=Path(root);source=root/'source'/source_name;matrix=source_matrix(units,up_axis)
    triangles=read_glb(source)['triangles'] if source.suffix.lower()=='.glb' else read_stl(source)
    triangles=[{'object_id':t['object_id'],'vertices':[transform(matrix,p) for p in t['vertices']]} for t in triangles]
    facts=mesh_facts(triangles);groups={}
    for triangle in triangles:
        group=groups.setdefault(triangle['object_id'],{'id':triangle['object_id'],'vertices':[],'faces':[]})
        start=len(group['vertices']);group['vertices'].extend(triangle['vertices']);group['faces'].append([start,start+1,start+2])
    write_glb(root/'preview/model.glb',list(groups.values()))
    atomic(root/'artifacts.json',{'schema_version':'1.0','native':'source/'+source_name,'preview':'preview/model.glb','script':'scripts/import_mesh.py','units':'mm','source_to_project':matrix,'preview_to_project':PREVIEW_TO_PROJECT,'bounding_box_project':facts['bounding_box_project'],'objects':[{'id':key} for key in groups],'reproducibility':'source mesh + explicit conversion script','capabilities':{'viewable':True,'annotatable':True,'editable':'mesh only; original parametric history unknown','rebuildable':'preview conversion only; original design history unavailable'}})
    return facts

def import_mesh(project, source, units, up_axis, variant=None, parent=None):
    source=Path(source).resolve();require(source.is_file(),'Source model missing')
    require(source.suffix.lower() in ('.glb','.stl'),'Direct import supports static GLB and binary STL; native CAD/Blender imports require an explicit backend script')
    source_matrix(units,up_axis)
    work=project.workspace_create(variant,parent);root=Path(work['path']);name='imported'+source.suffix.lower();shutil.copy2(source,root/'source'/name)
    atomic(root/'import.json',{'schema_version':'1.0','original_name':source.name,'source_hash':digest(source),'source_units':units,'source_up_axis':up_axis,'scripts_executed_from_source':False,'history_recovered':False})
    script="from pathlib import Path\nimport sys\nsys.path.insert(0,str(Path.cwd()/'dependencies'))\nfrom easy_to_3d.importing import rebuild_mesh\nrebuild_mesh(Path.cwd(),"+repr(name)+","+repr(units)+","+repr(up_axis)+")\n"
    (root/'scripts/import_mesh.py').write_text(script,encoding='utf-8')
    result=run(root,[sys.executable,'scripts/import_mesh.py'],180)
    require(result['status']=='succeeded','Import conversion failed; logs retained in workspace '+str(root))
    report=check(root)
    return {**work,'check_status':report['status'],'capabilities':{'viewable':True,'annotatable':True,'editable':'mesh only','rebuildable':'conversion only'},'next_action':'Review checks and publish this workspace; no source script was executed'}
