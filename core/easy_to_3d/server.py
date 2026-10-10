"""Loopback-only viewer server. No script execution endpoint."""
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
from .project import Project
from .storage import confined, ContractError, Conflict, uid, read, digest

WEB=Path(__file__).parent/'web'
if not WEB.exists(): WEB=Path(__file__).resolve().parents[2]/'viewer'

def make_server(project,port=0):
    project_root=Project(project).root; token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def output(self,status,value,kind='application/json',attachment=False):
            data=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(status); self.send_header('Content-Type',kind); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer')
            policy="sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data: blob:" if attachment else "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self' data: blob:; img-src 'self' data: blob:; frame-ancestors 'none'"
            self.send_header('Content-Security-Policy',policy)
            if attachment:self.send_header('Content-Disposition','attachment')
            self.end_headers(); self.wfile.write(data)
        def valid_host(self):
            return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
        def do_GET(self):
            if not self.valid_host(): return self.output(403,{'error':'Invalid host'})
            project=Project(project_root)
            path=unquote(urlparse(self.path).path)
            try:
                if path=='/api/project': return self.output(200,project.inspect())
                if path.startswith('/api/print-instructions/'):
                    from .delivery import instructions
                    return self.output(200,instructions(project,path.rsplit('/',1)[1],parse_qs(urlparse(self.path).query).get('language',['zh'])[0]))
                if path=='/api/session': return self.output(200,{'token':token})
                if path.startswith('/api/review/'):
                    return self.output(200,project.review(path.rsplit('/',1)[1]))
                if path.startswith('/api/verify/'):
                    return self.output(200,project.verify(path.rsplit('/',1)[1]))
                if path.startswith('/delivery/'):
                    parts=path.split('/')
                    if len(parts)!=4: raise ContractError('Invalid delivery path')
                    folder=confined(project.root,'deliveries/'+parts[2])
                    manifest=read(folder/'manifest.json')
                    if manifest['project_id']!=project.data['id'] or parts[3] not in manifest['files']:
                        raise ContractError('Resource not in delivery manifest')
                    file=confined(folder,parts[3])
                    if digest(file)!=manifest['files'][parts[3]]:raise ContractError('Delivery file changed')
                    return self.output(200,file.read_bytes(),{'.pdf':'application/pdf','.svg':'image/svg+xml','.json':'application/json'}.get(file.suffix,'application/octet-stream'),attachment=True)
                if path.startswith('/files/'):
                    relative=path[len('/files/'):]; target=confined(project.root,relative)
                    allowed=False
                    for version in project.versions():
                        prefix=version['directory']+'/'
                        if relative.startswith(prefix) and relative[len(prefix):] in version['files']:
                            if digest(target)!=version['files'][relative[len(prefix):]]:raise ContractError('Published file changed; integrity verification required')
                            allowed=True; break
                    if not allowed: raise ContractError('Resource not in published manifest')
                else: target=confined(WEB,'index.html' if path=='/' else path.lstrip('/'))
                if not target.is_file(): return self.output(404,{'error':'Not found'})
                mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.glb':'model/gltf-binary','.svg':'image/svg+xml','.json':'application/json','.pdf':'application/pdf'}.get(target.suffix,'application/octet-stream')
                return self.output(200,target.read_bytes(),mime,attachment=path.startswith('/files/'))
            except (ContractError,OSError,KeyError,ValueError) as error: return self.output(400,{'error':str(error)})
        def do_POST(self):
            origin=f'http://127.0.0.1:{self.server.server_port}'
            if not self.valid_host() or self.headers.get('Origin')!=origin or self.headers.get('X-Easy-To-3D-Token')!=token:
                return self.output(403,{'error':'Same-origin token required'})
            try:
                project=Project(project_root)
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=4*1024*1024: return self.output(413,{'error':'Invalid body length'})
                if self.headers.get('Content-Type')!='application/json': return self.output(415,{'error':'JSON required'})
                payload=json.loads(self.rfile.read(length)); path=urlparse(self.path).path
                parts=path.strip('/').split('/')
                if len(parts)==3 and parts[:2]==['api','confirm']:
                    expected=self.headers.get('If-Match')
                    if expected is None:return self.output(428,{'error':'Project revision required'})
                    value=project.confirm(parts[2],payload['kind'],payload['note'],int(expected.strip('"')))
                    return self.output(200,value)
                if len(parts)==4 and parts[:2]==['api','export']:
                    from .exporting import export
                    ident,profile=parts[2:]
                    if profile not in ('print','drawings'):raise ContractError('Unknown export profile')
                    expected=self.headers.get('If-Match')
                    if expected is None:return self.output(428,{'error':'Project revision required'})
                    project.reload()
                    if int(expected.strip('"'))!=project.data['revision']:raise Conflict('Project changed; refresh versions before exporting')
                    delivery_id=uid('delivery')
                    manifest=export(project,ident,profile,project.root/'deliveries'/delivery_id)
                    return self.output(200,{'manifest':manifest,'files':[{'name':name,'url':'/delivery/'+delivery_id+'/'+name} for name in manifest['files']]})
                if len(parts)!=4 or parts[:2]!=['api','review']: return self.output(404,{'error':'No such action'})
                ident,action=parts[2:]
                expected=self.headers.get('If-Match')
                if expected is None: return self.output(428,{'error':'If-Match review revision required'})
                revision=int(expected.strip('"'))
                if action=='save': value=project.review_update(ident,payload,revision)
                elif action=='submit': value=project.submit(ident,revision)
                else: return self.output(404,{'error':'No such action'})
                return self.output(200,value)
            except Conflict as error: return self.output(409,{'error':str(error)})
            except (ContractError,OSError,KeyError,TypeError,ValueError) as error: return self.output(400,{'error':str(error)})
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)

def serve(project,port=0,version=None):
    server=make_server(project,port)
    print(json.dumps({'url':f'http://127.0.0.1:{server.server_port}'+('?version='+version if version else ''),'project':str(Path(project).resolve())}),flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
