import argparse
import json
import sys
import zipfile
from pathlib import Path
from .project import Project
from .storage import ContractError, Conflict, read, atomic, confined, digest, now

def parser():
    p=argparse.ArgumentParser(prog='easy-to-3d'); p.add_argument('--json',action='store_true'); sub=p.add_subparsers(dest='command',required=True)
    doctor=sub.add_parser('doctor'); doctor.add_argument('--backend',choices=['freecad','blender','all'],default='all'); doctor.add_argument('--executable'); doctor.add_argument('--probe',action='store_true')
    project=sub.add_parser('project'); ps=project.add_subparsers(dest='action',required=True)
    init=ps.add_parser('init'); init.add_argument('--parent',required=True); init.add_argument('--name',required=True); init.add_argument('--feature',default='结构设计')
    inspect=ps.add_parser('inspect'); inspect.add_argument('--project',required=True)
    confirm=ps.add_parser('confirm'); confirm.add_argument('--project',required=True);confirm.add_argument('--version',required=True);confirm.add_argument('--kind',choices=['white_model','design','delivery'],required=True);confirm.add_argument('--note',required=True)
    req=sub.add_parser('requirements');req.add_argument('--project',required=True);req.add_argument('--file',required=True);req.add_argument('--revision',type=int,required=True);req.add_argument('--variant')
    variant=sub.add_parser('variant'); variant.add_argument('action',choices=['create']); variant.add_argument('--project',required=True); variant.add_argument('--name',required=True); variant.add_argument('--from',dest='source')
    work=sub.add_parser('workspace'); work.add_argument('action',choices=['create']); work.add_argument('--project',required=True); work.add_argument('--variant'); work.add_argument('--parent')
    imp=sub.add_parser('import');imp.add_argument('--project',required=True);imp.add_argument('--source',required=True);imp.add_argument('--units',choices=['mm','cm','m'],required=True);imp.add_argument('--up-axis',choices=['Y','Z'],required=True);imp.add_argument('--variant');imp.add_argument('--parent')
    run=sub.add_parser('run'); run.add_argument('--workspace',required=True); run.add_argument('--timeout',type=float,default=180); run.add_argument('argv',nargs=argparse.REMAINDER)
    cancel=sub.add_parser('cancel'); cancel.add_argument('--workspace',required=True); cancel.add_argument('--run-id',required=True)
    recover=sub.add_parser('recover'); recover.add_argument('--workspace',required=True)
    check=sub.add_parser('check'); check.add_argument('--workspace',required=True); check.add_argument('--profile',action='append',choices=['structure','print','patent'])
    version=sub.add_parser('version'); version.add_argument('action',choices=['publish','verify']); version.add_argument('--project',required=True); version.add_argument('--workspace'); version.add_argument('--version'); version.add_argument('--summary',default='候选版本')
    review=sub.add_parser('review'); review.add_argument('action',choices=['list','restore','claim','respond']); review.add_argument('--project',required=True); review.add_argument('--version'); review.add_argument('--annotation'); review.add_argument('--batch'); review.add_argument('--text'); review.add_argument('--result-version'); review.add_argument('--status',default='addressed'); review.add_argument('--submitted',action='store_true')
    view=sub.add_parser('view'); view.add_argument('--project',required=True); view.add_argument('--version'); view.add_argument('--port',type=int,default=0)
    draw=sub.add_parser('drawings');draw.add_argument('action',choices=['convert-pdf','check']);draw.add_argument('--workspace');draw.add_argument('--svg');draw.add_argument('--output')
    export=sub.add_parser('export'); export.add_argument('--project',required=True); export.add_argument('--version',required=True); export.add_argument('--profile',choices=['print','drawings'],required=True); export.add_argument('--output',required=True)
    snapshot=sub.add_parser('backup');snapshot.add_argument('--project',required=True);snapshot.add_argument('--output',required=True)
    audit=sub.add_parser('backup-verify');audit.add_argument('--file',required=True)
    guide=sub.add_parser('delivery-guide');guide.add_argument('--project',required=True);guide.add_argument('--version',required=True);guide.add_argument('--language',choices=['zh','en','ja','fr'],default='zh')
    return p

def dispatch(a):
    if a.command=='backup-verify':
        from .backup import verify_backup
        return verify_backup(a.file)
    if a.command=='recover':
        from .execution import recover
        return recover(a.workspace)
    if a.command=='cancel':
        from .execution import cancel
        return cancel(a.workspace,a.run_id)
    if a.command=='doctor':
        from .doctor import doctor
        return doctor(a.backend,a.executable,a.probe)
    if a.command=='run':
        from .execution import run
        command=a.argv[1:] if a.argv and a.argv[0]=='--' else a.argv
        return run(a.workspace,command,a.timeout)
    if a.command=='check':
        from .checks import check
        return check(a.workspace,a.profile or ['structure'])
    if a.command=='project' and a.action=='init':
        project=Project.init(a.parent,a.name,a.feature); return project.inspect()
    if a.command=='drawings':
        from .drawings import convert_pdf,check_drawings
        return convert_pdf(a.svg,a.output) if a.action=='convert-pdf' else check_drawings(a.workspace)
    project=Project(a.project)
    if a.command=='import':
        from .importing import import_mesh
        return import_mesh(project,a.source,a.units,a.up_axis,a.variant,a.parent)
    if a.command=='project':
        if a.action=='confirm':return project.confirm(a.version,a.kind,a.note)
        return project.inspect()
    if a.command=='requirements':return project.requirements_set(read(a.file),a.revision,a.variant)
    if a.command=='variant': return project.variant_create(a.name,a.source)
    if a.command=='workspace': return project.workspace_create(a.variant,a.parent)
    if a.command=='version':
        if a.action=='publish': return project.publish(a.workspace,a.summary)
        return project.verify(a.version)
    if a.command=='review':
        if a.action=='list':
            records=[{'version_id':v['id'],**project.review(v['id'])} for v in project.versions() if not a.version or v['id']==a.version]
            if a.submitted:
                for record in records: record['annotations']=[x for x in record['annotations'] if x.get('review_batch_id')]
            return records
        if a.action=='restore':
            candidates=[x for v in project.versions() for x in project.review(v['id'])['annotations'] if x['id']==a.annotation]
            if len(candidates)!=1: raise ContractError('Unknown annotation')
            return {'annotation':candidates[0],'version':project.version(candidates[0]['model_version_id'])}
        if a.action=='claim': return project.claim(a.version,a.batch)
        return project.respond(a.version,a.batch,a.annotation,a.text,a.result_version,a.status)
    if a.command=='view':
        from .server import serve
        if a.version: project.version(a.version)
        return serve(a.project,a.port,a.version)
    if a.command=='backup':
        from .backup import backup
        return backup(project,a.output)
    if a.command=='delivery-guide':
        from .delivery import instructions
        return instructions(project,a.version,a.language)
    if a.command=='export':
        from .exporting import export
        return export(project,a.version,a.profile,a.output)

def main(argv=None):
    # Stable JSON streams when Windows redirects a console with a legacy code page.
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    a=parser().parse_args(argv)
    try:
        result=dispatch(a)
        if result is not None: print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        if isinstance(result,dict) and result.get('status') in ('failed','timed_out','cancelled','fail'): return 3
        return 0
    except (ContractError,OSError,zipfile.BadZipFile,KeyError,TypeError,ValueError) as error:
        print(json.dumps({'error':str(error),'type':type(error).__name__},ensure_ascii=False),file=sys.stderr); return 4 if isinstance(error,Conflict) else 2

if __name__=='__main__': sys.exit(main())
