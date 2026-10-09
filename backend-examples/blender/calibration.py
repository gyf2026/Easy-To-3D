"""Run Blender --background --python this_script inside workspace.
Free mesh example, coordinates in metres/Z-up; explicit mapping to project mm.
"""
import bpy
from pathlib import Path
import sys
sys.path.insert(0,str(Path.cwd()/"dependencies"))
from easy_to_3d.glb import write_glb,PREVIEW_TO_PROJECT
from easy_to_3d.storage import atomic
root=Path.cwd();bpy.ops.wm.read_factory_settings(use_empty=True)
objects=[]
for ident,location,size in [('base',(.02,.012,.002),(.06,.04,.004)),('upright',(-.008,.012,.017),(.004,.03,.026))]:
    bpy.ops.mesh.primitive_cube_add(size=1,location=location);obj=bpy.context.object;obj.name=ident;obj.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);objects.append(obj)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'source/model.blend'))
meshes=[];points=[]
for obj in objects:
    mesh=obj.data;mesh.calc_loop_triangles();vertices=[list(obj.matrix_world@v.co) for v in mesh.vertices];vertices=[[x*1000 for x in p] for p in vertices];points+=vertices;meshes.append({'id':obj.name,'vertices':vertices,'faces':[list(t.vertices) for t in mesh.loop_triangles]})
write_glb(root/'preview/model.glb',meshes)
atomic(root/'artifacts.json',{'schema_version':'1.0','native':'source/model.blend','preview':'preview/model.glb','script':'scripts/calibration.py','units':'mm','source_to_project':[1000,0,0,0,0,1000,0,0,0,0,1000,0,0,0,0,1],'preview_to_project':PREVIEW_TO_PROJECT,'bounding_box_project':{'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]},'objects':[{'id':x.name,'name':x.name} for x in objects],'reproducibility':'script','backend':'blender'})
print('EASY_TO_3D_EXPORT_OK')
