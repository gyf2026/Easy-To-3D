"""Run as separate FreeCAD Python script after modeling in workspace.
Native OCCT hidden-line removal, standard views and experimental section/explosion.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path.cwd()/"dependencies"))
import FreeCAD as App
import Part, TechDraw
from easy_to_3d.storage import atomic,digest,read
root=Path.cwd();artifact=read(root/'artifacts.json');doc=App.openDocument(str(root/artifact['native']))
shapes=[o.Shape for o in doc.Objects if hasattr(o,'Shape') and not o.Shape.isNull()]
shape=Part.makeCompound(shapes);box=shape.BoundBox;extent=max(box.DiagonalLength,1)*1.1
views=[]
entries=[('front',[0,-1,0],shape),('top',[0,0,1],shape),('right',[1,0,0],shape),('isometric',[1,-1,1],shape)]
# Keep positive X half to expose interior; cut geometry is native, not image filtering.
cut=Part.makeBox(box.XLength+1,box.YLength+2,box.ZLength+2,App.Vector(box.Center.x,box.YMin-1,box.ZMin-1))
section=shape.common(cut)
if not section.isNull():entries.append(('section_experimental',[0,-1,0],section))
exploded=[]
for i,original in enumerate(shapes):
    part=original.copy();part.translate(App.Vector(0,0,i*max(box.ZLength,10)*.6));exploded.append(part)
if len(exploded)>1:entries.append(('exploded_experimental',[1,-1,1],Part.makeCompound(exploded)))
for i,(name,direction,geometry) in enumerate(entries,1):
    style={'stroke':'rgb(0,0,0)','stroke-width':'0.35','fill':'none'}
    projected=TechDraw.projectToSVG(geometry,App.Vector(*direction),vStyle=style,v0Style=style,v1Style=style)
    content=TechDraw.removeSvgTags(projected)
    local_extent=max(geometry.BoundBox.DiagonalLength*1.1,extent)
    # TechDraw SVG coordinates are native mm. Generous symmetric bounds retain line geometry.
    header=f'<svg xmlns="http://www.w3.org/2000/svg" width="180mm" height="180mm" viewBox="{-local_extent} {-local_extent} {local_extent*2} {local_extent*2}">'
    svg=header+'<rect x="'+str(-local_extent)+'" y="'+str(-local_extent)+'" width="'+str(local_extent*2)+'" height="'+str(local_extent*2)+'" fill="white"/>'+content+f'<text x="0" y="{local_extent*.9}" text-anchor="middle" font-size="{local_extent*.055}" fill="black">FIG. {i}</text></svg>'
    path=root/'drawings'/(name+'.svg');path.write_text(svg,encoding='utf-8')
    views.append({'name':name,'figure_number':i,'projection':'orthographic','camera_direction':direction,'svg':path.relative_to(root).as_posix(),'sha256':digest(path),'native_projection':'TechDraw.projectToSVG','experimental':name.endswith('experimental')})
atomic(root/'drawings/index.json',{'schema_version':'1.0','source_native_hash':digest(root/artifact['native']),'views':views,'part_labels':[],'referenced_part_numbers':[],'rule_profile':{'region':'CN','type':'invention-utility-model','verified_at':'2026-10-08','sources':['https://www.cnipa.gov.cn/art/2025/11/14/art_99_202568.html','https://www.cnipa.gov.cn/jact/front/mailpubdetail.do?sysid=6&transactId=485638'],'scope':'Consistency and readable black line figures; manual application review required'},'section_limit':'Simple half-space cut example, no section hatching; experimental','explosion_limit':'Manual static offsets; no automatic layout guarantee'})
print('EASY_TO_3D_DRAWINGS_OK')
