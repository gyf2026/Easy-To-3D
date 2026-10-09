"""Drawing metadata checks and optional host-side SVG -> vector PDF conversion."""
from pathlib import Path
import xml.etree.ElementTree as ET
from .storage import read,atomic,digest,now,confined
from .contracts import require

def convert_pdf(svg,output):
    try:import cairosvg
    except ImportError as error:raise ValueError('Install easy-to-3d[drawings] for PDF conversion; native SVG remains available') from error
    svg=Path(svg);tree=ET.fromstring(svg.read_bytes())
    # No external references or scripts in locally generated engineering drawings.
    for node in tree.iter():
        require(node.tag.split('}')[-1] not in ('script','foreignObject','image'),'Active or external SVG content unsupported')
        for key,value in node.attrib.items():
            require(not key.lower().startswith('on') and not key.endswith('href'),'External SVG resources unsupported')
            require('url(' not in value.lower(),'External SVG references unsupported')
    cairosvg.svg2pdf(bytestring=svg.read_bytes(),write_to=str(output),unsafe=False)
    return {'svg_hash':digest(svg),'pdf_hash':digest(output),'conversion':'CairoSVG vector conversion','created_at':now()}

def check_drawings(root):
    root=Path(root);config=read(root/'drawings/index.json');artifact=read(root/'artifacts.json')
    require(config.get('source_native_hash')==digest(confined(root,artifact['native'])),'Drawing native fingerprint mismatch')
    items=[];numbers=[x['figure_number'] for x in config['views']]
    items.append({'id':'unique_figure_numbers','status':'pass' if len(set(numbers))==len(numbers) else 'fail'})
    directions={'front':[0,-1,0],'top':[0,0,1],'right':[1,0,0]}
    for value in config['views']:
        path=confined(root,value['svg']);items.append({'id':'drawing_'+value['name'],'status':'pass' if path.is_file() and digest(path)==value['sha256'] else 'fail','evidence':value['svg']})
        if value['name'] in directions:items.append({'id':'direction_'+value['name'],'status':'pass' if value['projection']=='orthographic' and value['camera_direction']==directions[value['name']] else 'fail'})
    labels=config.get('part_labels',[]);ids=[x['number'] for x in labels]
    items.append({'id':'unique_part_labels','status':'pass' if len(set(ids))==len(ids) else 'fail'})
    referenced=config.get('referenced_part_numbers',[])
    items.append({'id':'referenced_parts','status':'pass' if set(referenced).issubset(set(ids)) else 'fail'})
    items.extend([{'id':'line_quality','status':'unknown','reason':'Human review required'},{'id':'patent_compliance','status':'unknown','reason':'Automatic checks cover consistency, not application compliance'}])
    report={'schema_version':'1.0','created_at':now(),'source_native_hash':config['source_native_hash'],'items':items,'rule_profile':config.get('rule_profile'),'status':'fail' if any(x['status']=='fail' for x in items) else 'unknown'}
    atomic(root/'checks/drawings.json',report);return report
