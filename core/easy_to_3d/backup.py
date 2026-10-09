"""Portable verified whole-project snapshots, separate from immutable model exports."""
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from .storage import lock, read, now, digest
from .contracts import require

def backup(project, output):
    output=Path(output).expanduser().resolve()
    require(not output.is_relative_to(project.root), 'Store backups outside the project directory')
    output.parent.mkdir(parents=True,exist_ok=True)
    with lock(project.root),lock(output.parent):
        require(not output.exists(),'Backup already exists; choose a new file')
        for execution in (project.root/'workspace').glob('*/execution.json'):
            require(read(execution).get('status')!='running','Execution is active; finish or recover it before backup')
        # Older immutable manifests may hash a snapshotted lock file. Preserve those bytes.
        historical_locks={project.root/v['directory']/name for v in project.versions() for name in v['files'] if Path(name).name=='.write.lock'}
        def included(path):return path.is_file() and (path.name!='.write.lock' or path in historical_locks)
        files={};directories=[]
        for path in sorted(project.root.rglob('*')):
            require(not path.is_symlink(),'Project contains a symbolic link; resolve it before a portable backup')
            if path.is_dir():directories.append(path.relative_to(project.root).as_posix()+'/')
            if not included(path):continue
            relative=path.relative_to(project.root).as_posix()
            files[relative]=digest(path)
        fd,temp=tempfile.mkstemp(prefix='.backup-',suffix='.zip',dir=output.parent);os.close(fd)
        try:
            manifest={'schema_version':'1.0','project_id':project.data['id'],'created_at':now(),'files':files,'directories':directories,'scope':'whole project; browser-only unsaved edits excluded'}
            with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as archive:
                for relative in directories:archive.writestr('project/'+relative,b'')
                for relative,expected in files.items():
                    path=project.root/relative;archive.write(path,'project/'+relative)
                    require(digest(path)==expected,'Project changed during backup; retry after active writes finish')
                archive.writestr('backup-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
            verified=verify_backup(temp)
            current={p.relative_to(project.root).as_posix():digest(p) for p in project.root.rglob('*') if included(p)}
            require(current==files,'Project changed during backup; retry after active writes finish')
            # Do not replace an archive created by a concurrent external writer.
            require(not output.exists(),'Backup already exists; choose a new file')
            with open(temp,'rb+') as stream:os.fsync(stream.fileno())
            os.replace(temp,output)
            return {'status':'pass','project_id':project.data['id'],'output':str(output),'sha256':digest(output),'file_count':verified['file_count']}
        finally:
            if os.path.exists(temp):os.unlink(temp)

def verify_backup(path):
    with zipfile.ZipFile(path) as archive:
        entries=archive.infolist();names=[entry.filename for entry in entries]
        require(len(names)==len(set(names)),'Duplicate backup entries')
        require('backup-manifest.json' in names,'Backup manifest missing')
        manifest=json.loads(archive.read('backup-manifest.json'))
        require(manifest.get('schema_version')=='1.0' and isinstance(manifest.get('files'),dict),'Unknown backup manifest')
        directories=manifest.get('directories',[])
        require(isinstance(directories,list),'Invalid backup directories')
        for name in [*manifest['files'],*directories]:
            relative=PurePosixPath(name)
            require(not relative.is_absolute() and '..' not in relative.parts and '\\' not in name and bool(relative.parts),'Unsafe backup path')
        require(set(names)=={'backup-manifest.json',*('project/'+name for name in manifest['files']),*('project/'+name for name in directories)},'Backup entries do not match manifest')
        for name,expected in manifest['files'].items():
            relative=PurePosixPath(name)
            require(not relative.is_absolute() and '..' not in relative.parts and '\\' not in name,'Unsafe backup path')
            hash_=hashlib.sha256()
            with archive.open('project/'+name) as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):hash_.update(chunk)
            require('sha256:'+hash_.hexdigest()==expected,'Backup integrity mismatch: '+name)
        return {'status':'pass','project_id':manifest['project_id'],'file_count':len(manifest['files'])}
