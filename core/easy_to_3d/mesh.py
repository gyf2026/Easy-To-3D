"""Small GLB triangle reader and STL writer for deterministic checks.
Unsupported compression/sparse/skinned geometry is rejected, never guessed.
"""
import json
import math
import struct
from pathlib import Path
from .contracts import require, transform, IDENTITY

MATERIAL_EXTENSIONS={'KHR_materials_unlit','KHR_materials_clearcoat','KHR_materials_ior',
    'KHR_materials_specular','KHR_materials_transmission','KHR_materials_volume',
    'KHR_materials_sheen','KHR_materials_iridescence','KHR_materials_emissive_strength',
    'KHR_materials_anisotropy','KHR_materials_dispersion','KHR_texture_transform'}

def read_glb(path, normalize_object_ids=False):
    data=Path(path).read_bytes()
    require(len(data)>=20,'Truncated GLB')
    magic,version,length=struct.unpack_from('<4sII',data)
    require(magic==b'glTF' and version==2 and length==len(data),'Invalid GLB header')
    chunks={}; offset=12
    while offset<len(data):
        require(offset+8<=len(data),'Truncated GLB chunk')
        size,kind=struct.unpack_from('<II',data,offset); offset+=8
        require(offset+size<=len(data),'Truncated chunk'); chunks[kind]=data[offset:offset+size]; offset+=size
    require(0x4E4F534A in chunks and 0x004E4942 in chunks,'GLB needs JSON and BIN chunks')
    doc=json.loads(chunks[0x4E4F534A]); binary=chunks[0x004E4942]
    unsupported=set(doc.get('extensionsRequired',[]))-MATERIAL_EXTENSIONS
    unsupported|=set(doc.get('extensionsUsed',[]))&{'KHR_draco_mesh_compression','EXT_meshopt_compression','KHR_mesh_quantization','KHR_texture_basisu','EXT_mesh_gpu_instancing'}
    require(not unsupported,'Unsupported GLB extensions: '+', '.join(sorted(unsupported))+'; export an uncompressed static GLB with embedded images')
    require(not doc.get('animations'),'Animated GLB unsupported; export a static pose with Blender')
    require(len(doc.get('buffers',[]))==1 and not doc['buffers'][0].get('uri'),'External GLB buffers unsupported')
    for image in doc.get('images',[]):
        require(not image.get('uri') or image['uri'].startswith('data:image/'),'External GLB images unsupported; embed textures before import')
    if normalize_object_ids:
        for index,node in enumerate(doc.get('nodes',[])):
            if 'mesh' in node:node.setdefault('extras',{})['object_id']='import_node_'+str(index)
    def accessor(index):
        item=doc['accessors'][index]; require(not item.get('sparse'),'Sparse accessors unsupported')
        fmt={5126:'f',5125:'I',5123:'H',5121:'B'}.get(item['componentType']); require(fmt is not None,'Unsupported component type')
        width={'SCALAR':1,'VEC3':3}.get(item['type']); require(width is not None,'Unsupported accessor type')
        v=doc['bufferViews'][item['bufferView']]; require(v.get('buffer',0)==0,'Unknown buffer')
        start=v.get('byteOffset',0)+item.get('byteOffset',0); size=struct.calcsize('<'+fmt)*width; stride=v.get('byteStride',size)
        require(stride>=size,'Invalid accessor stride')
        count=item['count']; require(isinstance(count,int) and 0<=count<=10000000,'Invalid accessor count')
        require(start>=v.get('byteOffset',0) and start+max(0,count-1)*stride+size<=v.get('byteOffset',0)+v['byteLength']<=len(binary),'Accessor exceeds buffer')
        values=[list(struct.unpack_from('<'+fmt*width,binary,start+i*stride)) for i in range(count)]
        require(all(math.isfinite(x) for row in values for x in row),'Nonfinite vertex data')
        return values
    def multiply(a,b):
        return [sum(a[r*4+k]*b[k*4+c] for k in range(4)) for r in range(4) for c in range(4)]
    def local(node):
        if 'matrix' in node: return [node['matrix'][c*4+r] for r in range(4) for c in range(4)]
        t=node.get('translation',[0,0,0]); s=node.get('scale',[1,1,1]); x,y,z,w=node.get('rotation',[0,0,0,1])
        rot=[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),t[0],2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),t[1],2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),t[2],0,0,0,1]
        for r in range(3):
            for c in range(3): rot[r*4+c]*=s[c]
        return rot
    triangles=[]; objects=[]; visited=set()
    def walk(index,parent,ancestors):
        require(index not in ancestors,'GLTF node cycle')
        node=doc['nodes'][index]; require('skin' not in node,'Skinned geometry unsupported'); m=multiply(parent,local(node))
        if 'mesh' in node:
            name=node.get('extras',{}).get('object_id') or node.get('name') or 'node_'+str(index)
            objects.append(name)
            for primitive in doc['meshes'][node['mesh']]['primitives']:
                require(primitive.get('mode',4)==4,'Only triangle primitives supported'); require(not primitive.get('targets'),'Morph targets unsupported')
                points=[transform(m,p) for p in accessor(primitive['attributes']['POSITION'])]
                indices=[x[0] for x in accessor(primitive['indices'])] if 'indices' in primitive else list(range(len(points)))
                require(len(indices)%3==0 and all(isinstance(x,int) and 0<=x<len(points) for x in indices),'Invalid triangle indices')
                triangles.extend({'object_id':name,'vertices':[points[indices[i+j]] for j in range(3)]} for i in range(0,len(indices),3))
        for child in node.get('children',[]): walk(child,m,ancestors|{index})
    scene=doc.get('scene',0)
    for index in doc['scenes'][scene]['nodes']: walk(index,IDENTITY,set())
    require(bool(triangles),'No triangle geometry')
    return {'triangles':triangles,'objects':objects,'document':doc}

def project_triangles(path,matrix):
    return [{'object_id':t['object_id'],'vertices':[transform(matrix,p) for p in t['vertices']]} for t in read_glb(path)['triangles']]

def normal(vertices):
    a,b,c=vertices; u=[b[i]-a[i] for i in range(3)]; v=[c[i]-a[i] for i in range(3)]
    n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]; length=math.sqrt(sum(x*x for x in n))
    return [x/length for x in n] if length>1e-14 else [0,0,0]

def write_stl(path,triangles):
    with Path(path).open('wb') as stream:
        stream.write(b'Easy-To-3D; coordinates in millimetres'.ljust(80,b' ')); stream.write(struct.pack('<I',len(triangles)))
        for triangle in triangles:
            points=triangle['vertices']; values=normal(points)+[x for p in points for x in p]; stream.write(struct.pack('<12fH',*values,0))

def read_stl(path):
    data=Path(path).read_bytes(); require(len(data)>=84,'Truncated binary STL'); count=struct.unpack_from('<I',data,80)[0]
    require(len(data)==84+count*50,'Invalid binary STL size')
    return [{'object_id':'stl','vertices':[list(struct.unpack_from('<3f',data,84+i*50+12+j*12)) for j in range(3)]} for i in range(count)]
