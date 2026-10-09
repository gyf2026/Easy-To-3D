"""Static hinge example; free scripting, no motion solver."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'dependencies'))
import FreeCAD as App,Part
from easy_to_3d.glb import write_glb,PREVIEW_TO_PROJECT
from easy_to_3d.storage import atomic,digest
from easy_to_3d.contracts import IDENTITY
root=Path.cwd();params=json.loads((root/'params.json').read_text()) if (root/'params.json').exists() else {};hole=params.get('mount_hole_radius_mm',2)
left=Part.makeBox(25,30,3,App.Vector(-30,-15,-5));right=Part.makeBox(25,30,3,App.Vector(5,-15,-5))
left=left.cut(Part.makeCylinder(hole,3,App.Vector(-18,0,-5)));right=right.cut(Part.makeCylinder(2,3,App.Vector(18,0,-5)))
for y in [-15,5]:
 tube=Part.makeCylinder(5,10,App.Vector(0,y,0),App.Vector(0,1,0)).cut(Part.makeCylinder(2.2,10,App.Vector(0,y,0),App.Vector(0,1,0)))
 bridge=Part.makeBox(5,10,3,App.Vector(-5,y,-5));left=left.fuse(bridge).fuse(tube)
tube=Part.makeCylinder(5,10,App.Vector(0,-5,0),App.Vector(0,1,0)).cut(Part.makeCylinder(2.2,10,App.Vector(0,-5,0),App.Vector(0,1,0)))
right=right.fuse(Part.makeBox(5,10,3,App.Vector(0,-5,-5))).fuse(tube)
axle=Part.makeCylinder(2,32,App.Vector(0,-16,0),App.Vector(0,1,0));doc=App.newDocument('StaticHinge');objects=[]
for ident,shape in [('left_leaf',left),('right_leaf',right),('axle',axle)]:obj=doc.addObject('PartDesign::Feature',ident);obj.Shape=shape;objects.append(obj)
doc.recompute();doc.saveAs(str(root/'source/model.FCStd'));Part.export(objects,str(root/'exports/model.step'))
mesh=[]
for obj in objects:
 vertices,faces=obj.Shape.tessellate(.05);mesh.append({'id':obj.Name,'vertices':[[v.x,v.y,v.z] for v in vertices],'faces':[list(f) for f in faces]})
write_glb(root/'preview/model.glb',mesh);bb=Part.makeCompound([o.Shape for o in objects]).BoundBox
atomic(root/'artifacts.json',{'schema_version':'1.0','native':'source/model.FCStd','preview':'preview/model.glb','script':'scripts/hinge.py','units':'mm','source_to_project':IDENTITY,'preview_to_project':PREVIEW_TO_PROJECT,'bounding_box_project':{'min':[bb.XMin,bb.YMin,bb.ZMin],'max':[bb.XMax,bb.YMax,bb.ZMax]},'objects':[{'id':o.Name} for o in objects],'reproducibility':'script-and-parameters','backend':'freecad'})
measured=next(f.Surface.Radius for f in left.Faces if isinstance(f.Surface,Part.Cylinder) and abs(f.Surface.Center.x+18)<1e-6)
atomic(root/'checks/native.json',{'schema_version':'1.0','source_native_hash':digest(root/'source/model.FCStd'),'items':[{'id':o.Name,'valid':o.Shape.isValid(),'solid_count':len(o.Shape.Solids),'volume_mm3':o.Shape.Volume} for o in objects],'measurements':{'width_mm':bb.XLength,'depth_mm':bb.YLength,'axle_radius_mm':next(f.Surface.Radius for f in axle.Faces if isinstance(f.Surface,Part.Cylinder)),'mount_hole_radius_mm':measured}})
print('EASY_TO_3D_EXPORT_OK')

atomic(root/"parameter-hints.json",{"schema_version":"1.0","items":[{"id":'mount_hole_radius_mm',"purpose":'一侧叶片安装孔半径',"value":hole,"units":"mm","object_ids":['left_leaf'],"source_script":"scripts/hinge.py"}]})
