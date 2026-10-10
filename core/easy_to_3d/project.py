"""Project identity, immutable publication, version-linked reviews."""
import copy
import re
import shutil
from pathlib import Path
from . import contracts as c
from .storage import atomic, read, lock, confined, digest, fingerprint, now, uid, ContractError, Conflict

class Project:
    def __init__(self, root):
        self.root=Path(root).resolve()
        self.data=read(self.root/'project.json')
        c.require(self.data.get('schema_version')=='1.0','Unknown project schema; refusing write')
        c.require(self.data.get('coordinates')=={'units':'mm','handedness':'right','up_axis':'Z'},'Unknown project coordinate semantics')

    @classmethod
    def init(cls, parent, name, feature=None, language='zh'):
        c.require(language in ('zh','en','ja','fr'),'Unsupported project language')
        feature=feature or {'zh':'结构设计','en':'Structural design','ja':'構造設計','fr':'Conception structurelle'}[language]
        def clean(s):
            s=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',s).strip(' .')[:48] or 'project'
            return '_'+s if s.upper().split('.')[0] in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))} else s
        from datetime import datetime
        project_id=uid('prj')
        root=Path(parent).resolve()/(datetime.now().strftime('%Y%m%d')+'_'+clean(name)+'_'+clean(feature)+'_'+project_id[-6:])
        root.mkdir(parents=True,exist_ok=False)
        for folder in ('references','requirements/history','variants','workspace','.cache'):
            (root/folder).mkdir(parents=True)
        atomic(root/'project.json',{'schema_version':'1.0','id':project_id,'name':name,'language':language,'created_at':now(),'coordinates':{'units':'mm','handedness':'right','up_axis':'Z'},'variants':[],'active_version_id':None,'phase':'requirements','revision':0})
        atomic(root/'requirements/current.json',{'schema_version':'1.0','revision':0,'items':[]})
        atomic(root/'state.json',{'schema_version':'1.0','accepted_versions':[],'confirmations':[]})
        notes={'zh':('项目说明.md','需求、假设与验收条件保存在 requirements/current.json。','默认方案'),'en':('Project notes.md','Requirements, assumptions and acceptance criteria are stored in requirements/current.json.','Default design'),'ja':('プロジェクト説明.md','要件、前提、検収条件は requirements/current.json に保存されます。','標準案'),'fr':('Notes du projet.md','Les exigences, hypothèses et critères de validation sont enregistrés dans requirements/current.json.','Conception par défaut')}[language]
        (root/notes[0]).write_text('# '+name+'\n\n'+notes[1]+'\n',encoding='utf-8')
        project=cls(root); project.variant_create(notes[2])
        return project

    def reload(self):
        self.data=read(self.root/'project.json'); return self.data

    def variant_create(self,name,source=None):
        with lock(self.root):
            self.reload()
            if source: self.version(source)
            variant_id=uid('var'); relative='variants/'+variant_id
            (self.root/relative/'versions').mkdir(parents=True)
            variant={'schema_version':'1.0','id':variant_id,'name':name,'from_version_id':source,'created_at':now()}
            atomic(self.root/relative/'variant.json',variant)
            if source:
                requirements=self.root/relative/'requirements';requirements.mkdir()
                (requirements/'history').mkdir()
                atomic(requirements/'current.json',read(self.version_root(source)/'requirements.snapshot.json'))
            self.data['variants'].append({'id':variant_id,'name':name,'path':relative})
            self.data['revision']+=1; atomic(self.root/'project.json',self.data)
            return variant

    def versions(self):
        self.reload(); result=[]
        for variant in self.data['variants']:
            for path in sorted(confined(self.root,variant['path']).glob('versions/*/version.json')):
                if path.parent.name.startswith('.'):
                    continue
                value=read(path); value['directory']=path.parent.relative_to(self.root).as_posix(); result.append(value)
        return sorted(result,key=lambda x:x['created_at'])

    def version(self,version_id):
        matches=[x for x in self.versions() if x['id']==version_id]
        c.require(len(matches)==1,'Unknown or ambiguous version: '+str(version_id))
        return matches[0]

    def version_root(self,version_id):
        return confined(self.root,self.version(version_id)['directory'])

    def workspace_create(self,variant_id=None,parent=None):
        self.reload()
        variant_id=variant_id or (self.version(parent)['variant_id'] if parent else self.data['variants'][0]['id'])
        c.require(any(x['id']==variant_id for x in self.data['variants']),'Unknown variant')
        if parent: self.version(parent)
        ident=uid('work'); root=self.root/'workspace'/ident; root.mkdir()
        for sub in ('source','scripts','preview','drawings','exports','checks','dependencies'):
            (root/sub).mkdir()
        # Examples use a local snapshot, independent of embedded Python's import paths.
        support=root/'dependencies/easy_to_3d'; support.mkdir()
        for module in Path(__file__).parent.glob('*.py'):
            shutil.copy2(module,support/module.name)
        atomic(root/'workspace.json',{'schema_version':'1.0','id':ident,'variant_id':variant_id,'parent_version_id':parent,'created_at':now(),'status':'incomplete'})
        variant=next(x for x in self.data['variants'] if x['id']==variant_id)
        variant_requirements=confined(self.root,variant['path'])/'requirements/current.json'
        atomic(root/'requirements.snapshot.json',read(variant_requirements if variant_requirements.exists() else self.root/'requirements/current.json'))
        return {'id':ident,'path':str(root)}

    def requirements_set(self,value,expected_revision,variant_id=None):
        c.require(isinstance(expected_revision,int),'Expected requirements revision required')
        c.require(isinstance(value,dict),'Requirements must be object'); c.require(value.get('schema_version')=='1.0','Unknown requirements schema')
        c.require(isinstance(value.get('items'),list),'Items required'); c.require(len(value['items'])<=10000,'Too many requirements')
        c.require(all(isinstance(x,dict) for x in value['items']),'Requirement must be object'); c.require(value.get('revision')==expected_revision,'Payload revision mismatch')
        c.require(c.requirements(value) is value,'Invalid requirements')
        with lock(self.root):
            self.reload();requirements_root=self.root/'requirements'
            if variant_id:
                variant=next((x for x in self.data['variants'] if x['id']==variant_id),None)
                c.require(variant is not None,'Unknown requirements variant')
                requirements_root=confined(self.root,variant['path'])/'requirements'
                if not (requirements_root/'current.json').exists():
                    (requirements_root/'history').mkdir(parents=True,exist_ok=True)
                    atomic(requirements_root/'current.json',read(self.root/'requirements/current.json'))
            old=read(requirements_root/'current.json')
            if old['revision']!=expected_revision: raise Conflict('Requirements changed; reload and merge')
            atomic(requirements_root/'history'/f"r{old['revision']:06d}.json",old)
            value=copy.deepcopy(value); value['revision']=expected_revision+1
            atomic(requirements_root/'current.json',value); return value

    def publish(self,workspace_id,summary):
        workspace=confined(self.root,'workspace/'+workspace_id)
        with lock(self.root):
            self.reload(); work=read(workspace/'workspace.json')
            c.require(work.get('schema_version')=='1.0','Unknown workspace schema')
            c.require(work.get('id')==workspace_id,'Workspace identity mismatch')
            if work.get('status')=='published':
                return self.version(work['result_version_id'])
            committed=[v for v in self.versions() if v.get('workspace_id')==workspace_id]
            c.require(len(committed)<=1,'Ambiguous committed publication; manual recovery required')
            if committed:
                version=committed[0]
                c.require(self.verify(version['id'])['artifacts']['status']=='pass','Committed publication changed; refusing recovery')
                self.reload()
                active=self.version(self.data['active_version_id']) if self.data['active_version_id'] else None
                if active is None or active['created_at']<=version['created_at']:
                    self.data['active_version_id']=version['id'];self.data['phase']='review';self.data['revision']+=1
                    atomic(self.root/'project.json',self.data)
                work.update(status='published',result_version_id=version['id']);atomic(workspace/'workspace.json',work)
                return self.version(version['id'])
            artifact=read(workspace/'artifacts.json')
            c.require(artifact.get('schema_version')=='1.0','Unknown artifact schema')
            c.require(artifact.get('units')=='mm','Project artifacts must explicitly use mm')
            c.matrix(artifact['source_to_project']); c.matrix(artifact['preview_to_project'])
            c.vector(artifact['bounding_box_project']['min']); c.vector(artifact['bounding_box_project']['max'])
            c.require(all(a<=b for a,b in zip(artifact['bounding_box_project']['min'],artifact['bounding_box_project']['max'])),'Inverted bounding box')
            c.require(isinstance(artifact.get('objects'),list),'Object inventory required')
            object_ids=[x['id'] for x in artifact['objects']]
            c.require(len(set(object_ids))==len(object_ids),'Duplicate object IDs')
            hints_path=workspace/'parameter-hints.json'
            if hints_path.exists():
                from .hints import validate
                artifact['parameter_hints']=validate(workspace,read(hints_path),object_ids)
            for key in ('native','preview','script'):
                c.require(isinstance(artifact.get(key),str), 'Missing '+key)
                file=confined(workspace,artifact[key]); c.require(file.is_file() and file.stat().st_size>0,'Missing or empty '+key)
            c.require(artifact['preview'].endswith('.glb'),'Preview must be GLB')
            source_suffix=Path(artifact['native']).suffix.lower()
            c.require(source_suffix in ('.fcstd','.blend','.glb','.stl'),'Source must be FCStd, blend, imported GLB or STL')
            if source_suffix in ('.glb','.stl'):
                provenance=read(workspace/'import.json')
                c.require(provenance.get('source_hash')==digest(confined(workspace,artifact['native'])),'Imported source hash mismatch')
                c.require(provenance.get('history_recovered') is False and provenance.get('scripts_executed_from_source') is False,'Imported mesh cannot claim recovered design history')
            from .mesh import read_glb
            read_glb(confined(workspace,artifact['preview']))
            execution=read(workspace/'execution.json')
            c.require(execution.get('status')=='succeeded' and execution.get('exit_code')==0,'Failed or incomplete execution cannot be published')
            c.requirements(read(workspace/'requirements.snapshot.json'))
            c.require((workspace/'checks/report.json').is_file(),'Check report required')
            from .checks import input_fingerprint
            report=read(workspace/'checks/report.json')
            c.require(report.get('input_fingerprint')==input_fingerprint(workspace),'Stale check report')
            if work['parent_version_id']: self.version(work['parent_version_id'])
            variant=next((x for x in self.data['variants'] if x['id']==work['variant_id']),None)
            c.require(variant is not None,'Unknown variant')
            existing=[x for x in self.versions() if x['variant_id']==variant['id']]
            ident=uid('ver'); sequence=max([x['sequence'] for x in existing],default=0)+1
            versions=confined(self.root,variant['path'])/'versions'
            temporary=versions/('.publishing_'+ident); temporary.mkdir()
            try:
                for source in workspace.rglob('*'):
                    if source.name=='.write.lock':continue
                    if source.is_symlink(): raise ContractError('Symlinks must be snapshotted before publishing')
                    if source.is_file() and source.name!='workspace.json':
                        relative=source.relative_to(workspace); target=temporary/relative; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)
                manifest={p.relative_to(temporary).as_posix():digest(p) for p in temporary.rglob('*') if p.is_file()}
                version={'schema_version':'1.0','id':ident,'project_id':self.data['id'],'variant_id':variant['id'],'workspace_id':workspace_id,'sequence':sequence,'parent_version_id':work['parent_version_id'],'created_at':now(),'summary':summary,'status':'candidate','artifacts':artifact,'files':manifest,'environment':execution.get('environment',{}),'reproducibility':artifact.get('reproducibility','unknown')}
                atomic(temporary/'version.json',version)
                review=temporary/'review'; review.mkdir()
                atomic(review/'record.json',{'schema_version':'1.0','revision':0,'annotations':[],'batches':[],'responses':[],'events':[]})
                temporary.rename(versions/f'v{sequence:03d}_{ident}')
                self.data['active_version_id']=ident; self.data['phase']='review'; self.data['revision']+=1
                atomic(self.root/'project.json',self.data)
                work['status']='published'; work['result_version_id']=ident; atomic(workspace/'workspace.json',work)
                return self.version(ident)
            finally:
                if temporary.exists(): shutil.rmtree(temporary)

    def verify(self,ident):
        version=self.version(ident); root=self.version_root(ident)
        differences=[]
        for relative,expected in version['files'].items():
            path=confined(root,relative)
            if not path.is_file() or digest(path)!=expected: differences.append(relative)
        inputs=[x for x in differences if x.startswith(('source/','scripts/','dependencies/','requirements.'))]
        return {'version_id':ident,'artifacts':{'status':'fail' if differences else 'pass','changed':differences},'input_snapshot':{'status':'fail' if inputs else 'pass','changed':inputs},'rebuild_environment':{'status':'unknown','recorded':version['environment'],'reason':'Compare runtime explicitly before rebuilding; does not block browsing'}}

    def review(self,ident):
        return read(self.version_root(ident)/'review/record.json')

    def review_update(self,ident,payload,expected_revision,actor='user'):
        c.require(actor in ('user','agent'),'Invalid actor')
        with lock(self.root):
            version=self.version(ident); root=self.version_root(ident); record=read(root/'review/record.json')
            if not isinstance(expected_revision,int) or record['revision']!=expected_revision: raise Conflict('Review changed; reload and merge your draft')
            c.require(payload.get('schema_version')=='1.0','Unknown review schema')
            c.require(isinstance(payload.get('annotations'),list),'Annotations required')
            c.require(len(payload['annotations'])<=10000,'Too many annotations')
            preview_hash=version['files'][version['artifacts']['preview']]
            old={x['id']:x for x in record['annotations']}; updated=[]; reopened=[]; seen=set()
            for incoming in payload['annotations']:
                value=copy.deepcopy(incoming); c.annotation(value,ident,preview_hash)
                key=value.get('id') or uid('ann'); c.require(isinstance(key,str) and key not in seen,'Duplicate annotation ID'); seen.add(key)
                previous=old.get(key)
                if previous:
                    c.require(value.get('revision')==previous['revision'],'Annotation revision mismatch')
                    if previous.get('review_batch_id'):
                        c.require(all(value.get(k)==previous.get(k) for k in ('text','anchor','view','review_batch_id','markup')),'Submitted annotations are immutable; create a new draft')
                    if actor=='agent': c.require(value['text']==previous['text'],'Agent cannot replace user text')
                    value['created_at']=previous['created_at']; value['creator']=previous['creator']
                    if value['status']=='accepted': c.require(actor=='user','Only user can accept')
                    if value['status']=='accepted' and previous['status']!='accepted':
                        c.require(previous['status']=='addressed','Only addressed issues can be accepted')
                    if actor=='user' and previous.get('review_batch_id'):
                        c.require(value['status'] in (previous['status'],'open','accepted','deleted'),'User can accept, reopen or soft-delete submitted issues')
                        if previous['status']!='open' and value['status']=='open':
                            followup=copy.deepcopy(previous)
                            followup.update(id=uid('ann'),status='open',revision=1,reopened_from=key,created_at=now(),updated_at=now())
                            followup.pop('review_batch_id',None)
                            reopened.append(followup)
                    if value==previous: updated.append(previous); continue
                    value['revision']=previous['revision']+1
                    record['events'].append({'id':uid('evt'),'at':now(),'actor':actor,'annotation_id':key,'before':previous,'after':value})
                else:
                    c.require(not value.get('review_batch_id'),'New annotations cannot assign a batch')
                    c.require(value['status']=='open','New annotations must be open')
                    value['created_at']=now(); value['creator']=actor; value['revision']=1
                value['id']=key; value['updated_at']=now(); updated.append(value)
            c.require(set(old).issubset(seen),'Delete annotations through status=deleted; history must be retained')
            record['annotations']=updated+reopened; record['revision']+=1; atomic(root/'review/record.json',record); return record

    def submit(self,ident,expected_revision):
        with lock(self.root):
            version=self.version(ident); root=self.version_root(ident); record=read(root/'review/record.json')
            if record['revision']!=expected_revision: raise Conflict('Review changed; reload before submitting')
            draft=[x for x in record['annotations'] if not x.get('review_batch_id') and x['status']!='deleted']
            c.require(bool(draft),'No saved draft annotations')
            batch={'schema_version':'1.0','id':uid('batch'),'model_version_id':ident,'preview_hash':version['files'][version['artifacts']['preview']],'annotation_ids':[x['id'] for x in draft],'submitted_at':now(),'status':'submitted'}
            for value in draft: value['review_batch_id']=batch['id']; value['revision']+=1
            record['batches'].append(batch); record['revision']+=1; atomic(root/'review/record.json',record)
            return {'batch':batch,'review':record,'continuation':f"处理项目 {self.data['name']}（ID {self.data['id']}，路径 {self.root}）的评审批次 {batch['id']}，源版本 {ident}。先恢复批注现场，再在新工作区修改并回归已确认需求。"}

    def claim(self,ident,batch_id):
        with lock(self.root):
            root=self.version_root(ident); record=read(root/'review/record.json')
            batch=next((x for x in record['batches'] if x['id']==batch_id),None); c.require(batch is not None,'Unknown batch')
            if batch['status']=='submitted':
                batch['status']='processing'; batch['task_id']=uid('task'); batch['claimed_at']=now(); record['revision']+=1; atomic(root/'review/record.json',record)
            return {'batch':batch,'annotations':[x for x in record['annotations'] if x.get('review_batch_id')==batch_id]}

    def respond(self,ident,batch_id,annotation_id,text,result_version=None,status='addressed'):
        c.require(status in ('addressed','needs_clarification','unresolved'),'Invalid response status')
        c.require(isinstance(text,str) and bool(text.strip()),'Response text required')
        if result_version:
            result=self.version(result_version)
            c.require(result['parent_version_id']==ident,'Result must derive from reviewed version')
        if status=='addressed': c.require(result_version is not None,'Addressed response needs result version')
        with lock(self.root):
            root=self.version_root(ident); record=read(root/'review/record.json')
            item=next((x for x in record['annotations'] if x['id']==annotation_id and x.get('review_batch_id')==batch_id),None); c.require(item is not None,'Annotation not in batch')
            response={'schema_version':'1.0','id':uid('resp'),'annotation_id':annotation_id,'batch_id':batch_id,'source_version_id':ident,'result_version_id':result_version,'text':text,'status':status,'created_at':now()}
            record['responses'].append(response); item['status']=status; item['revision']+=1
            batch=next(x for x in record['batches'] if x['id']==batch_id)
            batch['status']='completed' if all(x['status'] in ('addressed','accepted','needs_clarification','unresolved') for x in record['annotations'] if x.get('review_batch_id')==batch_id) else 'processing'
            record['revision']+=1; atomic(root/'review/record.json',record); return response

    def inspect(self):
        self.reload(); versions=self.versions(); pending=[]
        for version in versions:
            record=self.review(version['id'])
            pending += [{'version_id':version['id'],'batch_id':x['id'],'status':x['status']} for x in record['batches'] if x['status']!='completed']
        incomplete=[p.relative_to(self.root).as_posix() for p in (self.root/'workspace').glob('*/workspace.json') if read(p).get('status')!='published']
        staging=[p.relative_to(self.root).as_posix() for variant in self.data['variants'] for p in confined(self.root,variant['path']).glob('versions/.publishing_*')]
        return {'project':self.data,'path':str(self.root),'versions':versions,'pending_batches':pending,'requirements':read(self.root/'requirements/current.json'),'state':read(self.root/'state.json'),'incomplete_workspaces':incomplete,'recovery':{'uncommitted_publications':staging,'reason':'Staging directories are not visible versions. Original workspace retained; retry publication from it.'},'next_action':'Process pending batches' if pending else 'Resume incomplete workspace' if incomplete else 'Review selected version' if versions else 'Confirm requirements and create a white model'}

    def confirm(self,ident,kind,note,expected_revision=None):
        c.require(kind in ('white_model','design','delivery'),'Unknown confirmation kind')
        c.require(isinstance(note,str) and bool(note.strip()),'Record actual user confirmation text')
        self.version(ident)
        c.require(self.verify(ident)['artifacts']['status']=='pass','Changed version cannot be confirmed')
        with lock(self.root):
            self.reload()
            if expected_revision is not None and self.data['revision']!=expected_revision:raise Conflict('Project changed; refresh before confirming')
            state=read(self.root/'state.json')
            event={'id':uid('confirm'),'version_id':ident,'kind':kind,'user_note':note,'created_at':now()}
            state['confirmations'].append(event)
            if kind in ('design','delivery') and ident not in state['accepted_versions']:state['accepted_versions'].append(ident)
            atomic(self.root/'state.json',state)
            self.reload();self.data['phase']='refinement' if kind=='white_model' else 'delivery';self.data['revision']+=1;atomic(self.root/'project.json',self.data)
            return event
