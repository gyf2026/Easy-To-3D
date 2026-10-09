"""Purpose-specific facts; no report claims unknown native geometry passes."""
from collections import Counter
from pathlib import Path
from .storage import read, atomic, digest, fingerprint, now, confined
from .contracts import require
from .mesh import project_triangles, normal

def input_fingerprint(root):
    root=Path(root)
    files={p.relative_to(root).as_posix():digest(p) for p in root.rglob('*') if p.is_file() and not p.is_relative_to(root/'runs') and (not p.is_relative_to(root/'checks') or p.name in ('native.json','requirements.json','drawings.json')) and p.name not in ('workspace.json','execution.json') and not p.name.endswith('.log')}
    return fingerprint(files)

def mesh_facts(triangles):
    points=[p for t in triangles for p in t['vertices']]
    bbox={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
    edges=Counter(); directed=Counter(); degenerates=0; volume=0
    for triangle in triangles:
        vertices=triangle['vertices']; keys=[tuple(round(x,6) for x in p) for p in vertices]
        if normal(vertices)==[0,0,0]: degenerates+=1
        for i in range(3):
            a,b=keys[i],keys[(i+1)%3]; edges[tuple(sorted((a,b)))]+=1; directed[(a,b)]+=1
        a,b,c=vertices
        volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
    return {'triangle_count':len(triangles),'bounding_box_project':bbox,'size_mm':[bbox['max'][i]-bbox['min'][i] for i in range(3)],'boundary_edges':sum(x==1 for x in edges.values()),'nonmanifold_edges':sum(x>2 for x in edges.values()),'inconsistent_winding_edges':sum(count==2 and directed[(a,b)]!=directed[(b,a)] for (a,b),count in edges.items()),'degenerate_faces':degenerates,'signed_volume_mm3':volume,'weld_tolerance_mm':1e-6}

def check(root,profiles=('structure',)):
    root=Path(root); artifact=read(root/'artifacts.json'); require(all(p in ('structure','print','patent') for p in profiles),'Unknown check profile')
    triangles=project_triangles(confined(root,artifact['preview']),artifact['preview_to_project']); facts=mesh_facts(triangles)
    expected=artifact['bounding_box_project']; measured=facts['bounding_box_project']
    bbox_matches=all(abs(measured[k][i]-expected[k][i])<=.01 for k in ('min','max') for i in range(3))
    items=[{'id':'preview_bbox','status':'pass' if bbox_matches else 'fail','evidence':facts,'tolerance_mm':.01},{'id':'native_validity','status':'unknown','reason':'Needs backend native solid validation, not inferred from preview mesh'}]
    native_path=root/'checks/native.json'
    native=read(native_path) if native_path.exists() else None
    if native and native.get('source_native_hash')==digest(confined(root,artifact['native'])):
        valid=bool(native.get('items')) and all(x.get('valid') is True and x.get('solid_count',0)>0 for x in native['items'])
        items[1]={'id':'native_validity','status':'pass' if valid else 'fail','evidence':'checks/native.json','source_native_hash':native['source_native_hash']}
    elif native:
        items[1]={'id':'native_validity','status':'unknown','reason':'Native report fingerprint does not match current source'}
    if 'print' in profiles:
        for field in ('boundary_edges','nonmanifold_edges','inconsistent_winding_edges','degenerate_faces'):
            items.append({'id':'print_'+field,'status':'pass' if facts[field]==0 else 'fail','value':facts[field]})
        items.append({'id':'print_positive_volume','status':'pass' if facts['signed_volume_mm3']>0 else 'fail','value':facts['signed_volume_mm3']})
        config=read(root/'print-config.json') if (root/'print-config.json').exists() else {}
        for field in ('wall_thickness','clearance','supports','orientation'):
            items.append({'id':'print_'+field,'status':'unknown','reason':'Requires process conditions and geometry-specific verification'})
        if config.get('build_volume_mm'):
            volume=config['build_volume_mm']; require(len(volume)==3 and all(isinstance(x,(int,float)) and x>0 for x in volume),'Invalid build volume')
            items.append({'id':'print_build_volume','status':'pass' if all(a<=b for a,b in zip(facts['size_mm'],volume)) else 'fail'})
    if 'patent' in profiles:
        items.append({'id':'patent_rules','status':'unknown','reason':'Drawing and current regional rules must be independently verified'})
    requirements=read(root/'requirements.snapshot.json')
    for item in requirements['items']:
        if item['status'] in ('confirmed','assumed'):
            result={'id':'requirement_'+item['id'],'status':'unknown','reason':'Needs declared measurement evidence','priority':item['priority']}
            method=item.get('verification')
            if isinstance(method,dict) and method.get('type')=='native_measurement' and native and native.get('source_native_hash')==digest(confined(root,artifact['native'])):
                measured=native.get('measurements',{}).get(method.get('key'))
                target=item.get('value'); tolerance=method.get('tolerance_mm',.01)
                from .contracts import number
                if number(measured) and number(target) and number(tolerance) and tolerance>=0:
                    result={'id':'requirement_'+item['id'],'status':'pass' if abs(measured-target)<=tolerance else 'fail','measured':measured,'expected':target,'tolerance':tolerance,'evidence':'checks/native.json','priority':item['priority']}
            items.append(result)
    report={'schema_version':'1.0','created_at':now(),'profiles':list(profiles),'input_fingerprint':input_fingerprint(root),'status':'fail' if any(x['status']=='fail' for x in items) else 'unknown' if any(x['status']=='unknown' for x in items) else 'pass','items':items}
    atomic(root/'checks/report.json',report); return report
