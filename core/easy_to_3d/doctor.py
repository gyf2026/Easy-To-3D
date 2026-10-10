"""Discovery is separate from actual script/export success."""
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from .execution import run
from .storage import now

DOWNLOADS={'freecad':'https://www.freecad.org/downloads.php','blender':'https://www.blender.org/download/'}

def discover(backend,explicit=None):
    if explicit:
        candidate=Path(os.path.expandvars(str(explicit).strip().strip('"'))).expanduser()
        return str(candidate.resolve()) if candidate.is_file() else None
    names=['FreeCADCmd','freecadcmd','FreeCAD','freecad'] if backend=='freecad' else ['blender']
    for name in names:
        result=shutil.which(name)
        if result:return result
    candidates=[Path('/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd'),Path('/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd'),Path('/Applications/FreeCAD.app/Contents/MacOS/FreeCAD')] if backend=='freecad' else [Path('/Applications/Blender.app/Contents/MacOS/Blender')]
    candidates += [Path.home()/str(p).lstrip('/') for p in candidates]
    if platform.system()=='Windows':
        candidates=[]
        for variable in ('ProgramFiles','ProgramFiles(x86)','LOCALAPPDATA'):
            location=os.environ.get(variable)
            if not location:continue
            base=Path(location)
            patterns=['FreeCAD*/bin/FreeCADCmd.exe','FreeCAD*/bin/freecadcmd.exe','Programs/FreeCAD*/bin/FreeCADCmd.exe'] if backend=='freecad' else ['Blender Foundation/Blender*/blender.exe','Programs/Blender Foundation/Blender*/blender.exe']
            for pattern in patterns:candidates.extend(sorted(base.glob(pattern),reverse=True))
    for candidate in candidates:
        if candidate.is_file(): return str(candidate)
    return None

def _probe_doctor(backend='all',explicit=None,probe=False):
    results=[]
    for name in ['freecad','blender'] if backend=='all' else [backend]:
        path=discover(name,explicit); result={'backend':name,'executable':path,'found':bool(path),'version':None,'script_export':'unknown','download':DOWNLOADS[name]}
        if path:
            try:
                process=subprocess.run([path,'--version'],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=15)
                result['launch']='pass' if process.returncode==0 else 'fail'; result['version']=(process.stdout+process.stderr).strip()[:1000]
            except (OSError,subprocess.TimeoutExpired) as error:result['launch']='fail';result['error']=str(error)
            if probe:
                with tempfile.TemporaryDirectory(prefix='easy-to-3d-probe-') as temp:
                    root=Path(temp); script=root/'probe.py'
                    if name=='blender':
                        script.write_text("import bpy\nbpy.ops.wm.read_factory_settings(use_empty=True)\nbpy.ops.mesh.primitive_cube_add(size=0.01)\nbpy.ops.wm.save_as_mainfile(filepath='probe.blend')\nbpy.ops.export_scene.gltf(filepath='probe.glb',export_format='GLB')\n",encoding='utf-8')
                        command=[path,'--background','--python',str(script)]; native=root/'probe.blend'
                    else:
                        script.write_text("import FreeCAD as App, Part\nd=App.newDocument('Probe')\no=d.addObject('PartDesign::Feature','Probe');o.Shape=Part.makeBox(10,12,14)\nd.recompute();d.saveAs('probe.FCStd');Part.export([o],'probe.step')\n",encoding='utf-8')
                        command=[path,str(script)]; native=root/'probe.FCStd'
                    execution=run(root,command,90); exported=root/('probe.glb' if name=='blender' else 'probe.step')
                    result['script_export']='pass' if execution['status']=='succeeded' and native.is_file() and exported.is_file() else 'fail'
                    result['probe']={'status':execution['status'],'exit_code':execution['exit_code'],'native_written':native.is_file(),'export_written':exported.is_file(),'stdout':(root/'build.stdout.log').read_text(encoding='utf-8',errors='replace')[-1000:],'stderr':(root/'build.stderr.log').read_text(encoding='utf-8',errors='replace')[-1000:]}
        else: result['launch']='unknown';result['next_step']='未找到工具：如果已安装，请提供可执行程序完整路径；否则从官方入口下载对应系统和处理器架构的稳定版，安装后重新自检。'
        if not path or result.get('launch')=='fail' or result.get('script_export')=='fail':
            result['setup_guidance']={
                'provided_path':str(explicit) if explicit else None,
                'configure_command':['easy-to-3d','--json','doctor','--backend',name,'--executable','<可执行程序完整路径>','--probe'],
                'download':DOWNLOADS[name],
                'installation_workflow':'未安装时，由 Agent 提出官方版本、系统架构、安装位置及权限需求；经用户同意后执行下载与安装，核验官方提供的校验信息，配置路径并重新运行实际探测。',
                'recommended_configuration':{'python':'3.10 或以上（核心运行环境）','backend':'官方稳定版；优先复现项目已验证版本，其他版本安装后需通过实际探测','validated_version':'FreeCAD 1.1.4 (macOS/Windows中文路径流程实测)' if name=='freecad' else 'Blender 4.5.3 LTS (macOS); 4.5.10 / 5.2.1 LTS (Windows)' ,'architecture':'与操作系统及处理器架构匹配；macOS arm64和Windows AMD64有局部实测，其他架构待验证'},
                'executable_hint':'选择实际可执行文件，不是安装目录、安装包或 .app 文件夹；macOS Blender 通常为 Blender.app/Contents/MacOS/Blender；FreeCAD 为 FreeCAD.app 内的 freecadcmd。Windows 选择对应 .exe；Linux 选择命令文件。',
                'verification':'路径存在仅表示找到工具；必须分别通过启动和脚本/导出探测。缺少一个后端时可使用满足任务的另一个，不要求同时安装。'}
        results.append(result)
    return {'schema_version':'1.0','tested_at':now(),'platform':platform.platform(),'backends':results,'session_capabilities':{'vision':'unknown','execution':'unknown','image_generation':'unknown','reason':'Must be tested in host Agent session, cannot be inferred from model name or environment variable'},'compatibility':'Actual local probe only; other platforms unverified'}

def doctor(backend='all',explicit=None,probe=False,cache=None,refresh=False,session=None):
    """Optional local cache; client facts are always supplied for the current session."""
    from datetime import datetime,timezone
    from .storage import read,atomic
    from .workflow import session_report
    client=session_report(session)
    paths={name:discover(name,explicit) for name in (['freecad','blender'] if backend=='all' else [backend])}
    fingerprint={'platform':platform.platform(),'backend':backend,'explicit':str(explicit),'probe':probe,'tools':{}}
    for name,path in paths.items():
        try:
            stat=Path(path).stat() if path else None
            fingerprint['tools'][name]=[path,stat.st_size,stat.st_mtime_ns] if stat else [None]
        except OSError:fingerprint['tools'][name]=[path,'unavailable']
    report=None
    if cache and not refresh:
        try:
            saved=read(cache);age=(datetime.now(timezone.utc)-datetime.fromisoformat(saved['tested_at'])).total_seconds()
            if saved.get('cache_fingerprint')==fingerprint and 0<=age<=7*86400 and not any(x.get('launch')=='fail' or x.get('script_export')=='fail' for x in saved.get('backends',[])):
                report=saved;report['cache_status']='reused'
        except (OSError,ValueError,KeyError,TypeError,AttributeError):pass
    if report is None:
        report=_probe_doctor(backend,explicit,probe);report['cache_fingerprint']=fingerprint;report['cache_status']='fresh'
        # Failures are not reused: fixing permissions or runtime dependencies must trigger a new probe.
        if cache:
            if any(x.get('launch')=='fail' or x.get('script_export')=='fail' for x in report['backends']):
                Path(cache).unlink(missing_ok=True)
            else:atomic(cache,report)
    report['client_capabilities']=client
    report['user_summary']={'available':[x['backend'] for x in report['backends'] if x['script_export']=='pass'],
        'needs_probe':[x['backend'] for x in report['backends'] if x['found'] and x['script_export']=='unknown'],
        'next_step':'Use the task-appropriate available route; probe or install only what this task needs. Never require every backend.'}
    return report
