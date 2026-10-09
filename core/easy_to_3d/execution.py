"""Explicit subprocess execution with bounded lifetime, logs and recovery."""
import os
import platform
import signal
import subprocess
import time
from pathlib import Path
from .storage import atomic, now, read, uid, lock, ContractError
from .contracts import require

def run(root, command, timeout=180):
    root=Path(root).resolve()
    # Separate lock directory so cancellation can write while the run owns its lock.
    guard=root/"runs";guard.mkdir(parents=True,exist_ok=True)
    with lock(guard,timeout=.1):
        recover(root, locked=True)
        return _run(root,command,timeout)

def _identity(pid, strict=False):
    if os.name=='nt':
        from .windows_process import identity
        try:return identity(pid)
        except OSError:
            if strict:raise ContractError('Process identity unavailable; manual cleanup required')
            return None
    try:
        result=subprocess.run(['ps','-p',str(pid),'-o','lstart=','-o','pgid=','-o','uid='],capture_output=True,text=True)
    except OSError:
        if strict: raise ContractError("Process identity unavailable; manual cleanup required")
        return None
    return result.stdout.strip() or None

def recover(root, locked=False):
    """Only kill a recorded process whose start time/group/owner still match."""
    root=Path(root).resolve();guard=root/'runs';guard.mkdir(parents=True,exist_ok=True)
    if not locked:
        with lock(guard,timeout=.1): return recover(root,locked=True)
    if not (root/'execution.json').exists(): return {'status':'nothing_to_recover'}
    record=read(root/'execution.json')
    if record.get('status')!='running': return {'status':'nothing_to_recover'}
    pid=record.get('pid');identity=record.get('process_identity')
    if pid:
        require(identity is not None,'Process identity cannot be verified; manual cleanup required')
    if pid and _identity(pid,strict=True):
        require(identity is not None and _identity(pid,strict=True)==identity,'Process identity cannot be verified; manual cleanup required')
        if os.name=='nt':
            from .windows_process import recover_job
            require(record.get('windows_job'), 'Missing Windows job identity; manual cleanup required')
            recover_job(record['windows_job'],pid,identity)
        else:os.killpg(pid,signal.SIGTERM)
        deadline=time.monotonic()+2
        while _identity(pid,strict=True)==identity and time.monotonic()<deadline: time.sleep(.05)
        if _identity(pid,strict=True)==identity:
            require(os.name!='nt','Windows process still active; manual cleanup required')
            os.killpg(pid,signal.SIGKILL)
    record.update(status='interrupted',finished_at=now(),error='Execution controller interrupted; recorded process recovered')
    atomic(root/'execution.json',record);atomic(guard/record['id']/'execution.json',record)
    import shutil
    for name in ('stdout','stderr'):
        source=root/f'build.{name}.log'
        if source.exists(): shutil.copy2(source,guard/record['id']/f'{name}.log')
    return record

def cancel(root, run_id):
    root=Path(root).resolve();record=read(root/"execution.json")
    require(record.get("id")==run_id and record.get("status")=="running","Run is no longer active")
    atomic(root/"cancel.json",{"run_id":run_id,"requested_at":now()})
    return {"status":"cancellation_requested","run_id":run_id}

def _run(root, command, timeout=180):
    root=Path(root).resolve(); require(isinstance(command,list) and command and all(isinstance(x,str) for x in command),'Command must be argv list')
    require(0<timeout<=3600,'Timeout must be between 0 and 3600 seconds')
    run_id=uid('run'); archive=root/'runs'/run_id;archive.mkdir(parents=True)
    from .freecad_command import prepare
    effective_command,adapter=prepare(root,command,archive)
    record={'schema_version':'1.0','id':run_id,'command':command,'started_at':now(),'controller_pid':os.getpid(),'status':'running','environment':{'platform':platform.platform(),'python':platform.python_version(),'executable':command[0]},'stdout':f'runs/{run_id}/stdout.log','stderr':f'runs/{run_id}/stderr.log'}
    if adapter:record.update(effective_command=effective_command,command_adapter=adapter)
    atomic(root/'execution.json',record); started=time.monotonic()
    job=None
    try:
        with (root/'build.stdout.log').open('wb') as out, (root/'build.stderr.log').open('wb') as err:
            if os.name=='nt':
                import json,sys
                from .windows_process import Job
                job=Job('EasyTo3D-'+run_id);record['windows_job']=job.name
                launcher=[sys.executable,str(Path(__file__).with_name('windows_bootstrap.py')),json.dumps(effective_command)]
                process=subprocess.Popen(launcher,cwd=root,stdout=out,stderr=err,stdin=subprocess.PIPE)
                try:
                    job.assign(process)
                except BaseException:
                    process.kill();process.wait();raise
            else:
                process=subprocess.Popen(effective_command,cwd=root,stdout=out,stderr=err,start_new_session=True)
            record['pid']=process.pid;record['process_identity']=_identity(process.pid); atomic(root/'execution.json',record)
            if job:
                process.stdin.write(b'1');process.stdin.close()
            try:
                while process.poll() is None:
                    request=read(root/'cancel.json') if (root/'cancel.json').exists() else {}
                    if request.get('run_id')==run_id:
                        raise KeyboardInterrupt('Cancellation requested')
                    remaining=timeout-(time.monotonic()-started)
                    if remaining<=0: raise subprocess.TimeoutExpired(command,timeout)
                    try: process.wait(timeout=min(.1,remaining))
                    except subprocess.TimeoutExpired: pass
                code=process.returncode; record['status']='succeeded' if code==0 else 'failed'
            except subprocess.TimeoutExpired:
                if job: job.terminate()
                else: os.killpg(process.pid,signal.SIGTERM)
                try: process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    if job: job.terminate()
                    else: os.killpg(process.pid,signal.SIGKILL)
                    process.wait()
                code=process.returncode; record['status']='timed_out'
            record['exit_code']=code
    except (OSError,KeyboardInterrupt) as error:
        record['status']='failed' if isinstance(error,OSError) else 'cancelled'; record['error']=str(error); record['exit_code']=None
        if 'process' in locals() and process.poll() is None:
            if job: job.terminate()
            else: os.killpg(process.pid,signal.SIGKILL)
            process.wait()
    finally:
        if 'process' in locals() and process.stdin is not None and not process.stdin.closed:process.stdin.close()
        if job:job.close()
    import shutil
    for name in ('stdout','stderr'):
        shutil.copy2(root/f'build.{name}.log',archive/f'{name}.log')
    record['duration_seconds']=time.monotonic()-started; record['finished_at']=now(); atomic(archive/'execution.json',record);atomic(root/'execution.json',record)
    return record

def revision_policy(attempts,max_rounds=3,max_seconds=900):
    if len(attempts)>=max_rounds: return {'continue':False,'reason':'revision round limit reached'}
    if sum(x.get('duration_seconds',0) for x in attempts)>=max_seconds: return {'continue':False,'reason':'time limit reached'}
    if attempts and attempts[-1].get('status') in ('failed','timed_out','cancelled'): return {'continue':False,'reason':'execution failure'}
    if len(attempts)>=2:
        if attempts[-1].get('error_fingerprint') and attempts[-1].get('error_fingerprint')==attempts[-2].get('error_fingerprint'): return {'continue':False,'reason':'same error repeated'}
        if attempts[-1].get('score',0)<attempts[-2].get('score',0): return {'continue':False,'reason':'quality regressed'}
    return {'continue':True,'reason':'within limits'}
