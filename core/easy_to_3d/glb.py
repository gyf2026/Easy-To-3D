"""Dependency-free GLB writer for backend-tessellated geometry.
Input coordinates are project mm/Z-up. GLB stores metres/Y-up with an
explicit inverse mapping in artifacts.json. No geometry rescaling heuristics.
"""
import json
import struct
from pathlib import Path

PREVIEW_TO_PROJECT=[1000,0,0,0, 0,0,-1000,0, 0,1000,0,0, 0,0,0,1]

def rewrite_json(source, target, document):
    """Preserve GLB binary chunks, UVs, textures and materials; replace only JSON."""
    data=Path(source).read_bytes();chunks=[];offset=12
    while offset<len(data):
        size,kind=struct.unpack_from('<II',data,offset);offset+=8
        payload=data[offset:offset+size];offset+=size
        if kind==0x4E4F534A:
            payload=json.dumps(document,ensure_ascii=False,separators=(',',':')).encode('utf-8')
            payload+=b' '*((-len(payload))%4)
        chunks.append(struct.pack('<II',len(payload),kind)+payload)
    body=b''.join(chunks)
    Path(target).write_bytes(struct.pack('<4sII',b'glTF',2,12+len(body))+body)

def write_glb(path,objects):
    blob=bytearray(); views=[]; accessors=[]; meshes=[]; nodes=[]
    for obj in objects:
        points=[[p[0]/1000,p[2]/1000,-p[1]/1000] for p in obj['vertices']]
        start=len(blob)
        for p in points:blob.extend(struct.pack('<3f',*p))
        view=len(views);views.append({'buffer':0,'byteOffset':start,'byteLength':len(points)*12,'target':34962})
        position=len(accessors);accessors.append({'bufferView':view,'componentType':5126,'count':len(points),'type':'VEC3','min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]})
        start=len(blob);indices=[i for face in obj['faces'] for i in face]
        for index in indices:blob.extend(struct.pack('<I',index))
        view=len(views);views.append({'buffer':0,'byteOffset':start,'byteLength':len(indices)*4,'target':34963})
        index_accessor=len(accessors);accessors.append({'bufferView':view,'componentType':5125,'count':len(indices),'type':'SCALAR'})
        meshes.append({'primitives':[{'attributes':{'POSITION':position},'indices':index_accessor,'material':0}]})
        nodes.append({'name':obj['id'],'mesh':len(meshes)-1,'extras':{'object_id':obj['id']}})
    doc={'asset':{'version':'2.0','generator':'Easy-To-3D'},'scene':0,'scenes':[{'nodes':list(range(len(nodes)))}],'nodes':nodes,'meshes':meshes,'materials':[{'pbrMetallicRoughness':{'baseColorFactor':[.73,.8,.86,1],'metallicFactor':0,'roughnessFactor':.8}}],'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':accessors}
    raw=json.dumps(doc,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);blob+=b'\x00'*((-len(blob))%4)
    Path(path).write_bytes(struct.pack('<4sII',b'glTF',2,12+8+len(raw)+8+len(blob))+struct.pack('<II',len(raw),0x4E4F534A)+raw+struct.pack('<II',len(blob),0x004E4942)+blob)
