"""Freely authored enclosure example with posts and separate lid."
"""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'dependencies'))
import FreeCAD as App,Part
from easy_to_3d.glb import write_glb,PREVIEW_TO_PROJECT
from easy_to_3d.storage import atomic,digest
from easy_to_3d.contracts import IDENTITY
root=Path.cwd();params=json.loads((root/'params.json').read_text()) if (root/'params.json').exists() else {};radius=params.get('post_hole_radius_mm',1.5)
wall=2;body=Part.makeBox(70,50,25).cut(Part.makeBox(66,46,25,App.Vector(2,2,2)))
for x,y in [(8,8),(62,8),(8,42),(62,42)]:
 post=Part.makeCylinder(4,10,App.Vector(x,y,2));post=post.cut(Part.makeCylinder(radius,10,App.Vector(x,y,2)));body=body.fuse(post)
lid=Part.makeBox(70,50,2,App.Vector(0,0,27));doc=App.newDocument('Enclosure');objects=[]
for ident,shape in [('body',body),('lid',lid)]:obj=doc.addObject('PartDesign::Feature',ident);obj.Shape=shape;objects.append(obj)
doc.recompute();doc.saveAs(str(root/'source/model.FCStd'));Part.export(objects,str(root/'exports/model.step'))
mesh=[]
for obj in objects:
 vertices,faces=obj.Shape.tessellate(.05);mesh.append({'id':obj.Name,'vertices':[[v.x,v.y,v.z] for v in vertices],'faces':[list(f) for f in faces]})
write_glb(root/'preview/model.glb',mesh);bb=Part.makeCompound([o.Shape for o in objects]).BoundBox
atomic(root/'artifacts.json',{'schema_version':'1.0','native':'source/model.FCStd','preview':'preview/model.glb','script':'scripts/enclosure.py','units':'mm','source_to_project':IDENTITY,'preview_to_project':PREVIEW_TO_PROJECT,'bounding_box_project':{'min':[bb.XMin,bb.YMin,bb.ZMin],'max':[bb.XMax,bb.YMax,bb.ZMax]},'objects':[{'id':o.Name} for o in objects],'reproducibility':'script-and-parameters','backend':'freecad'})
# Read native surfaces and bounds instead of using input parameter as evidence.
cylinders=[f.Surface for f in body.Faces if isinstance(f.Surface,Part.Cylinder)];inner=min(c.Radius for c in cylinders)
atomic(root/'checks/native.json',{'schema_version':'1.0','source_native_hash':digest(root/'source/model.FCStd'),'items':[{'id':o.Name,'valid':o.Shape.isValid(),'solid_count':len(o.Shape.Solids),'volume_mm3':o.Shape.Volume} for o in objects],'measurements':{'width_mm':body.BoundBox.XLength,'depth_mm':body.BoundBox.YLength,'height_mm':body.BoundBox.ZLength,'post_hole_radius_mm':inner,'lid_thickness_mm':lid.BoundBox.ZLength}})
print('EASY_TO_3D_EXPORT_OK')

atomic(root/"parameter-hints.json",{"schema_version":"1.0","items":[{"id":'post_hole_radius_mm',"purpose":'支撑柱安装孔半径',"value":radius,"units":"mm","object_ids":['body'],"source_script":"scripts/enclosure.py"}]})
