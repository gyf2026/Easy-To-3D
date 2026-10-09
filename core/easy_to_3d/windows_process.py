"""Windows native job objects contain backend descendants and die with the controller.

Imported only on Windows. No shell/taskkill dependency and no PID-only recovery.
"""
import ctypes
from ctypes import wintypes as w

kernel=ctypes.WinDLL('kernel32',use_last_error=True)
class BasicLimits(ctypes.Structure):
    _fields_=[('PerProcessUserTimeLimit',ctypes.c_int64),('PerJobUserTimeLimit',ctypes.c_int64),('LimitFlags',w.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',w.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',w.DWORD),('SchedulingClass',w.DWORD)]
class IOCounters(ctypes.Structure):
    _fields_=[(name,ctypes.c_uint64) for name in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
class ExtendedLimits(ctypes.Structure):
    _fields_=[('BasicLimitInformation',BasicLimits),('IoInfo',IOCounters),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
for name,args,result in [
    ('CreateJobObjectW',[ctypes.c_void_p,w.LPCWSTR],w.HANDLE),
    ('OpenJobObjectW',[w.DWORD,w.BOOL,w.LPCWSTR],w.HANDLE),
    ('SetInformationJobObject',[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD],w.BOOL),
    ('AssignProcessToJobObject',[w.HANDLE,w.HANDLE],w.BOOL),
    ('TerminateJobObject',[w.HANDLE,w.UINT],w.BOOL),
    ('OpenProcess',[w.DWORD,w.BOOL,w.DWORD],w.HANDLE),
    ('GetProcessTimes',[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)],w.BOOL),
    ('WaitForSingleObject',[w.HANDLE,w.DWORD],w.DWORD),
    ('IsProcessInJob',[w.HANDLE,w.HANDLE,ctypes.POINTER(w.BOOL)],w.BOOL),
    ('CloseHandle',[w.HANDLE],w.BOOL)]:
    fn=getattr(kernel,name);fn.argtypes=args;fn.restype=result

def checked(result):
    if not result: raise ctypes.WinError(ctypes.get_last_error())
    return result

def identity(pid):
    handle=kernel.OpenProcess(0x101000,False,pid) # QUERY_LIMITED_INFORMATION | SYNCHRONIZE
    if not handle:
        error=ctypes.get_last_error()
        if error==87: return None # PID no longer exists
        raise ctypes.WinError(error)
    try:
        state=kernel.WaitForSingleObject(handle,0)
        if state==0:return None
        if state!=258:raise ctypes.WinError(ctypes.get_last_error())
        times=[w.FILETIME() for _ in range(4)]
        checked(kernel.GetProcessTimes(handle,*[ctypes.byref(t) for t in times]))
        return f'windows:{pid}:{times[0].dwHighDateTime}:{times[0].dwLowDateTime}'
    finally:kernel.CloseHandle(handle)

class Job:
    def __init__(self,name):
        self.name=name;self.handle=checked(kernel.CreateJobObjectW(None,name))
        try:
            limits=ExtendedLimits();limits.BasicLimitInformation.LimitFlags=0x2000 # KILL_ON_JOB_CLOSE
            checked(kernel.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)))
        except BaseException:self.close();raise
    def assign(self,process):
        handle=checked(kernel.OpenProcess(0x0101,False,process.pid)) # SET_QUOTA | TERMINATE
        try:checked(kernel.AssignProcessToJobObject(self.handle,handle))
        finally:kernel.CloseHandle(handle)
    def terminate(self):checked(kernel.TerminateJobObject(self.handle,1))
    def close(self):
        if self.handle:kernel.CloseHandle(self.handle);self.handle=None

def recover_job(name,pid,expected_identity):
    from .contracts import require
    handle=kernel.OpenJobObjectW(0x000C,False,name) # QUERY | TERMINATE
    if not handle:
        if ctypes.get_last_error()==2:return False
        raise ctypes.WinError(ctypes.get_last_error())
    process=None
    try:
        process=kernel.OpenProcess(0x101000,False,pid)
        if not process:
            if ctypes.get_last_error()==87:return False
            raise ctypes.WinError(ctypes.get_last_error())
        # Keep the process handle open while checking creation time and Job membership.
        require(identity(pid)==expected_identity,'Windows process identity changed; refusing cleanup')
        belongs=w.BOOL();checked(kernel.IsProcessInJob(process,handle,ctypes.byref(belongs)))
        require(bool(belongs.value),'Recorded Windows process does not belong to the recorded Job; refusing cleanup')
        checked(kernel.TerminateJobObject(handle,1));return True
    finally:
        if process:kernel.CloseHandle(process)
        kernel.CloseHandle(handle)
