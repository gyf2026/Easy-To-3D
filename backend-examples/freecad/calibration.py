"""Run with FreeCADCmd inside an Easy-To-3D workspace.
Independent free script example: asymmetric plate and upright with offset holes.
Pass dimensions through params.json; preserve editable native solid.
"""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path.cwd()/"dependencies"))
import FreeCAD as App
import Part
from easy_to_3d.glb import write_glb, PREVIEW_TO_PROJECT
from easy_to_3d.storage import atomic,digest
from easy_to_3d.contracts import IDENTITY
root=Path.cwd()
params=json.loads((root/'params.json').read_text()) if (root/'params.json').exists() else {}
hole_radius=params.get('main_hole_radius_mm',3)
width,height,thickness=60,40,4
base=Part.makeBox(width,height,thickness,App.Vector(-10,-8,0))
for x,y,radius in [(0,0,hole_radius),(35,20,3)]:base=base.cut(Part.makeCylinder(radius,thickness,App.Vector(x,y,0)))
upright=Part.makeBox(4,30,26,App.Vector(-10,-3,4))
upright=upright.cut(Part.makeCylinder(4,4,App.Vector(-10,12,18),App.Vector(1,0,0)))
doc=App.newDocument('AsymmetricBracket')
objects=[]
for ident,shape in [('base',base),('upright',upright)]:
    obj=doc.addObject('PartDesign::Feature',ident);obj.Label=ident;obj.Shape=shape;objects.append(obj)
doc.recompute();doc.saveAs(str(root/'source/model.FCStd'))
Part.export(objects,str(root/'exports/model.step'))
mesh=[]
for obj in objects:
    vertices,faces=obj.Shape.tessellate(.05)
    mesh.append({'id':obj.Name,'vertices':[[v.x,v.y,v.z] for v in vertices],'faces':[list(f) for f in faces]})
write_glb(root/'preview/model.glb',mesh)
combined=Part.makeCompound([x.Shape for x in objects]);bb=combined.BoundBox
atomic(root/'artifacts.json',{'schema_version':'1.0','native':'source/model.FCStd','preview':'preview/model.glb','script':'scripts/calibration.py','units':'mm','source_to_project':IDENTITY,'preview_to_project':PREVIEW_TO_PROJECT,'bounding_box_project':{'min':[bb.XMin,bb.YMin,bb.ZMin],'max':[bb.XMax,bb.YMax,bb.ZMax]},'objects':[{'id':x.Name,'name':x.Label} for x in objects],'reproducibility':'script-and-parameters','backend':'freecad'})
atomic(root/'checks/native.json',{'schema_version':'1.0','items':[{'id':x.Name,'valid':x.Shape.isValid(),'solid_count':len(x.Shape.Solids),'volume_mm3':x.Shape.Volume} for x in objects],'source_native_hash':digest(root/'source/model.FCStd'),'measurements':{'base_width_mm':base.BoundBox.XLength,'base_depth_mm':base.BoundBox.YLength,'base_thickness_mm':base.BoundBox.ZLength,'main_hole_radius_mm':next(face.Surface.Radius for face in base.Faces if isinstance(face.Surface,Part.Cylinder) and abs(face.Surface.Center.x)<1e-6 and abs(face.Surface.Center.y)<1e-6),'other_hole_radius_mm':next(face.Surface.Radius for face in base.Faces if isinstance(face.Surface,Part.Cylinder) and abs(face.Surface.Center.x-35)<1e-6 and abs(face.Surface.Center.y-20)<1e-6),'cylinders':[{'radius_mm':face.Surface.Radius,'center':list(face.Surface.Center),'axis':list(face.Surface.Axis)} for face in base.Faces if isinstance(face.Surface,Part.Cylinder)]},'bounds':{'min':[bb.XMin,bb.YMin,bb.ZMin],'max':[bb.XMax,bb.YMax,bb.ZMax]}})
print('EASY_TO_3D_EXPORT_OK')

atomic(root/"parameter-hints.json",{"schema_version":"1.0","items":[{"id":'main_hole_radius_mm',"purpose":'底板第一个孔半径',"value":hole_radius,"units":"mm","object_ids":['base'],"source_script":"scripts/calibration.py"}]})
