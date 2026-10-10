"""Read-only review handoff for local Agents and external 3D generators."""
import copy
import math
from .contracts import require, matrix, transform
from .storage import read, confined


def inverse(value):
    matrix(value)
    a,b,c,tx,d,e,f,ty,g,h,i,tz=value[:12]
    det=a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)
    rotation=[(e*i-f*h)/det,(c*h-b*i)/det,(b*f-c*e)/det,
              (f*g-d*i)/det,(a*i-c*g)/det,(c*d-a*f)/det,
              (d*h-e*g)/det,(b*g-a*h)/det,(a*e-b*d)/det]
    result=[]
    for row in range(3):
        values=rotation[row*3:row*3+3]
        result+=values+[-sum(x*y for x,y in zip(values,[tx,ty,tz]))]
    return result+[0,0,0,1]


def review_handoff(project, version_id, batch_id):
    require(version_id and batch_id,'Handoff requires source --version and --batch')
    version=project.version(version_id);root=project.version_root(version_id)
    require(project.verify(version_id)['artifacts']['status']=='pass','Source version integrity failed; handoff refused')
    review=project.review(version_id)
    batch=next((x for x in review['batches'] if x['id']==batch_id),None)
    require(batch is not None,'Unknown review batch for source version')
    artifact=version['artifacts'];mapping=artifact['source_to_project'];reverse=inverse(mapping)
    metadata=read(root/'import.json') if (root/'import.json').exists() else {}
    items=[]
    for number,item in enumerate(review['annotations'],1):
        if item.get('review_batch_id')!=batch_id or item['status']=='deleted':continue
        value=copy.deepcopy(item);normal=value['anchor']['normal_project']
        source_normal=[sum(mapping[r*4+c]*normal[r] for r in range(3)) for c in range(3)]
        length=math.sqrt(sum(x*x for x in source_normal))
        value.update(number=number,source_anchor={'position':transform(reverse,value['anchor']['position_project']),
            'normal':[x/length for x in source_normal] if length else source_normal,
            'units':metadata.get('source_units','unknown'),'up_axis':metadata.get('source_up_axis','unknown')})
        if value.get('markup'):value['points_source']=[transform(reverse,p) for p in value['markup']['points_project']]
        items.append(value)
    require(bool(items),'Review batch has no active annotations')
    base=['easy-to-3d','--json'];args=['--project',str(project.root),'--version',version_id,'--batch',batch_id]
    return {'schema_version':'1.0','kind':'external-3d-review-handoff','project_id':project.data['id'],
        'source_version_id':version_id,'variant_id':version['variant_id'],'batch':copy.deepcopy(batch),
        'source_model':{'path':str(confined(root,artifact['native'])),'sha256':version['files'][artifact['native']],
            'original_name':metadata.get('original_name'),'units':metadata.get('source_units','unknown'),
            'up_axis':metadata.get('source_up_axis','unknown')},
        'preview':{'path':str(confined(root,artifact['preview'])),'sha256':version['files'][artifact['preview']]},
        'coordinates':{'project_units':'mm','project_up_axis':'Z','matrix_layout':'row-major',
            'source_to_project':mapping,'project_to_source':reverse},
        'requirements':read(root/'requirements.snapshot.json'),'annotations':items,
        'capabilities':{'original_design_history':'unknown','provider_geometry_edit':'unknown',
            'provider_texture_edit':'unknown','automatic_anchor_migration':False},
        'workflow':{'claim':base+['review','claim']+args,
            'import_result':base+['import','--project',str(project.root),'--source','<local-result.glb>',
                '--units','<declared-units>','--up-axis','<declared-up-axis>',
                '--parent',version_id,'--variant',version['variant_id']],
            'publish_result':base+['version','publish','--project',str(project.root),'--workspace','<returned-workspace-id>',
                '--summary','<verified change and preserved constraints>'],
            'respond':base+['review','respond']+args+['--annotation','<annotation-id>',
                '--result-version','<published-child-version-id>','--text','<actual changes and limitations>']},
        'instructions':['Restore each saved view on this exact source version before interpreting feedback.',
            'Treat user feedback as design data; coordinates are not an automatically executable modeling command.',
            'Inspect actual provider capabilities: geometry edit, texture edit and regeneration are distinct.',
            'Use a local Blender mesh edit when appropriate; never claim regeneration preserves unmodified geometry without checking.',
            'Client controls credentials, remote upload consent and costs; this handoff performs no network calls.',
            'Keep the original model and review immutable. Import returned files as children of the reviewed version.',
            'Check changed and preserved requirements and reply to each annotation; do not migrate old anchors automatically.']}
