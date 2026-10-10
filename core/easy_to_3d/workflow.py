"""Explicit capability evidence and task routing; no natural-language parsing."""
from datetime import datetime, timezone
from .contracts import require
from .storage import now

TASKS=('organic','precision','mesh-edit','texture','save','print')
CAPABILITIES=('generation','geometry_edit','texture_edit','local_download','execution','vision','slicing')

def session_report(value):
    result={'context':{},'tested_at':None,'capabilities':{key:{'status':'unknown','reason':'Not tested in this client session'} for key in CAPABILITIES}}
    if value is None:return result
    require(isinstance(value,dict),'Session report must be an object')
    context=value.get('context',{})
    require(isinstance(context,dict) and all(isinstance(context.get(key),str) and context[key].strip() for key in ('client','model','tools_fingerprint')),'Session report needs client, model and tools_fingerprint context')
    try:
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(value['tested_at'])).total_seconds()
    except (KeyError,ValueError,TypeError):require(False,'Session report needs a timezone-aware tested_at')
    require(isinstance(value.get('capabilities'),dict),'Session report needs capabilities')
    result.update(context=context,tested_at=value['tested_at'])
    for key,item in value['capabilities'].items():
        require(key in CAPABILITIES,'Unknown session capability: '+str(key))
        require(isinstance(item,dict) and item.get('status') in ('pass','fail','unknown'),'Invalid session capability status')
        require(item['status']!='pass' or isinstance(item.get('evidence'),str) and bool(item['evidence'].strip()),'Passing capability needs actual evidence')
        result['capabilities'][key]=dict(item) if 0<=age<=7*86400 else {'status':'unknown','reason':'Evidence expired; retest this session'}
    result['provenance']='Agent-supplied evidence; core cannot independently test host tools. Use only in the recorded client/model/tools context.'
    return result

def guide(task,report=None):
    require(task in TASKS,'Unknown workflow task')
    report=report or {};raw_session=report.get('client_capabilities');session=session_report(raw_session if raw_session and raw_session.get('tested_at') else None)
    capabilities=session.get('capabilities',{})
    backends={item['backend']:item for item in report.get('backends',[])}
    try:report_age=(datetime.now(timezone.utc)-datetime.fromisoformat(report['tested_at'])).total_seconds()
    except (KeyError,TypeError,ValueError):report_age=-1
    fresh=0<=report_age<=7*86400
    import platform
    from pathlib import Path
    fingerprint=report.get('cache_fingerprint',{})
    if fingerprint.get('platform')!=platform.platform():fresh=False
    for key,item in backends.items():
        path=item.get('executable')
        if path:
            try:
                stat=Path(path).stat();unchanged=fingerprint.get('tools',{}).get(key)==[path,stat.st_size,stat.st_mtime_ns]
            except OSError:unchanged=False
            if not unchanged:item=dict(item,script_export='unknown');backends[key]=item
    def available(key):return capabilities.get(key,{}).get('status')=='pass'
    def local(key):
        item=backends.get(key,{})
        if fresh and item.get('script_export')=='pass':return 'ready'
        if item.get('found') and item.get('launch')=='pass':return 'probe_required'
        return 'setup_required'
    candidates={'organic':['client-generation','blender'], 'precision':['freecad'],
                'mesh-edit':['client-geometry-edit','blender'], 'texture':['client-texture-edit','blender'],
                'save':['project-backup'],'print':['verified-export-and-slicing']}[task]
    states={'client-generation':'ready' if available('generation') and available('local_download') else 'capability_check_required',
            'client-geometry-edit':'ready' if available('geometry_edit') and available('local_download') else 'capability_check_required',
            'client-texture-edit':'ready' if available('texture_edit') and available('local_download') else 'capability_check_required',
            'freecad':local('freecad'),'blender':local('blender'),'project-backup':'ready','verified-export-and-slicing':'configuration_required'}
    selected=next((name for name in candidates if states[name]=='ready'),None)
    if selected is None:selected=next((name for name in candidates if states[name]=='probe_required'),candidates[0])
    return {'schema_version':'1.0','tested_at':now(),'task':task,'selected_route':selected,'route_status':states[selected],
        'routes':[{'route':name,'status':states[name]} for name in candidates],
        'questions':{'organic':['Only missing direction, appearance and intended size'],
          'precision':['Only missing critical dimensions, fit and preserved constraints'],
          'mesh-edit':['Only ambiguous feedback; restore the exact source version and view'],
          'texture':['Only missing appearance requirements; do not claim geometry changes'],
          'save':['Exact version and backup destination, only if not established'],
          'print':['Only missing printer, firmware, nozzle, material, layer height and approved profile']}[task],
        'permissions':['Request concrete installation consent only when the needed tool is missing',
          'Use existing authorization for remote uploads, paid calls and installation; otherwise obtain it before that action'],
        'validation':['Verify files, declared units/up-axis, required dimensions and visual constraints before review',
          'Repair verified failures and recheck; failed execution cannot be published',
          'Separate measured pass, subjective user confirmation and unknown; never infer printable from generation success'],
        'revision':['Read review handoff for the exact submitted source and batch',
          'Prefer verified geometry-edit capability; otherwise use local Blender or explicit CAD reconstruction',
          'If regeneration is needed, explain possible changes to preserved structure before proceeding',
          'Publish a child of the reviewed source, reply individually, then open the same-view comparison'],
        'delivery':['Preserve native files, scripts, requirements, feedback and evidence; verify whole-project backup',
          'Use delivery-guide for supported STL export and printer-specific slicing; unsupported formats need explicit conversion',
          'Never rename STL to G-code or deliver machine files without verified slicing configuration'],
        'agent_instructions':'Inspect available host tools first. Unknown is not missing or pass. Choose the route by design requirements, explain it in one short sentence, and ask only task-blocking questions. Keep tool setup, modeling, save and export in the Agent conversation; the viewer is for observation and feedback.'}
