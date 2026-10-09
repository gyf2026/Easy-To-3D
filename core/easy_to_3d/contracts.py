"""Shared semantic validation; unknown key semantics never silently accepted."""
import math
from .storage import ContractError

IDENTITY = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

def require(condition, message):
    if not condition:
        raise ContractError(message)

def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def vector(value, length=3):
    require(isinstance(value, list) and len(value) == length and all(number(x) for x in value), 'Expected finite vector of length ' + str(length))
    return value

def matrix(value):
    vector(value, 16)
    require(value[12:16] == [0,0,0,1], 'Matrices are row-major affine transforms')
    a,b,c,_, d,e,f,_, g,h,i,_ = value[:12]
    require(abs(a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)) > 1e-15, 'Transform is singular')
    return value

def transform(matrix_value, point):
    matrix(matrix_value); vector(point)
    return [sum(matrix_value[row*4+k]*point[k] for k in range(3))+matrix_value[row*4+3] for row in range(3)]

def view(value):
    require(isinstance(value, dict), 'View must be an object')
    require(value.get('state_version') == '1.0', 'Unknown display state version')
    require(value.get('projection') in ('orthographic','perspective'), 'Unknown projection')
    p,t,u = [vector(value.get(k)) for k in ('position_project','target_project','up')]
    direction = [t[i]-p[i] for i in range(3)]
    cross = [direction[1]*u[2]-direction[2]*u[1], direction[2]*u[0]-direction[0]*u[2], direction[0]*u[1]-direction[1]*u[0]]
    require(sum(x*x for x in cross)>1e-16, 'Degenerate camera')
    for key in ('aspect','near','far'):
        require(number(value.get(key)) and value[key]>0, 'Invalid camera ' + key)
    require(value['far']>value['near'], 'Invalid clipping range')
    key = 'orthographic_height' if value['projection']=='orthographic' else 'fov_degrees'
    require(number(value.get(key)) and value[key]>0, 'Missing camera projection parameter')
    if key=='fov_degrees':
        require(value[key]<179, 'Invalid field of view')
    require(isinstance(value.get('hidden_objects'),list) and all(isinstance(x,str) for x in value['hidden_objects']), 'Invalid hidden objects')
    require(value.get('clipping_planes') == [], 'Clipping is not supported in v1')
    require(value.get('display_mode') in ('solid','wireframe'), 'Unknown display mode')
    return value

def annotation(value, version, preview_hash):
    require(isinstance(value,dict), 'Annotation must be object')
    require(value.get('schema_version')=='1.0', 'Unknown annotation schema')
    require(value.get('model_version_id')==version, 'Annotation version mismatch')
    require(value.get('preview_hash')==preview_hash, 'Annotation preview hash mismatch')
    anchor=value.get('anchor',{})
    require(anchor.get('units')=='mm', 'Anchor units must be mm')
    vector(anchor.get('position_project')); vector(anchor.get('normal_project'))
    require(abs(sum(x*x for x in anchor['normal_project'])-1)<.001,'Normal must have unit length')
    require(isinstance(value.get('text'),str) and 0<len(value['text'].strip())<=10000, 'Annotation text required, maximum 10000 characters')
    require(value.get('status') in ('open','acknowledged','addressed','accepted','needs_clarification','unresolved','deleted'), 'Unknown annotation status')
    markup=value.get('markup')
    if markup is not None:
        require(isinstance(markup,dict),'Markup must be object')
        require(set(markup)=={'type','style','units','points_project','object_hints'},'Unknown or missing markup fields')
        require(markup['type'] in ('line','ruler','freehand'),'Unknown markup type')
        require(markup['style'] in ('solid','dashed'),'Unknown markup line style')
        require(markup['units']=='mm','Markup units must be mm')
        points=markup['points_project']; hints=markup['object_hints']
        require(isinstance(points,list) and 2<=len(points)<=4096,'Markup requires 2 to 4096 points')
        if markup['type']!='freehand':require(len(points)==2,'Straight line and ruler require two endpoints')
        for point in points: vector(point)
        require(points[0]==anchor['position_project'],'Markup anchor must match first endpoint')
        require(any(sum((a-b)**2 for a,b in zip(points[i-1],points[i]))>1e-12 for i in range(1,len(points))),'Markup must contain a nonzero segment')
        require(isinstance(hints,list) and len(hints)==len(points) and all(isinstance(x,str) and x for x in hints),'Markup requires matching point object hints')
    view(value.get('view'))
    return value

def requirements(value):
    require(value.get('schema_version')=='1.0', 'Unknown requirements schema')
    require(isinstance(value.get('items'),list), 'Requirements items required')
    ids=set()
    for item in value['items']:
        require(isinstance(item.get('id'),str) and item['id'] not in ids,'Duplicate or missing requirement ID')
        ids.add(item['id'])
        require(item.get('status') in ('proposed','confirmed','assumed','superseded'),'Unknown requirement status')
        require(item.get('priority') in ('hard','preference'),'Unknown requirement priority')
        require(isinstance(item.get('description'),str) and bool(item['description'].strip()),'Requirement description required')
        require('source' in item and 'verification' in item,'Requirement source and verification required')
    return value
