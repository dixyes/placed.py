#!/usr/bin/python

# simple Python LACE Daemon (fake

from flask import Flask, request, abort, current_app, render_template
from enum import Enum
import json,redis,pyotp,werkzeug.exceptions,struct,binascii,os,sys
import base64 as b64
from hilbertcanvas import HilbertCanvas
from flask_sockets import Sockets

# use your ext_auth
from custedauth import ext_auth

# colding time
cdt = 10

redis_port = int(os.environ.get('DB_PORT_6379_TCP_PORT',6379))
redis_host = os.environ.get('DB_PORT_6379_TCP_ADDR',"localhost")

app = Flask(__name__)
app.debug = True
sockets = Sockets(app)

# return code in json result
class RC(Enum):
    OK = 0
    NotFound = -404
    BadReq = -400
    AuthFail = -403
    IntErr = -500
    ReqLimit = -503

# json result
class JsonResponse():
    def __init__(self,code = RC.OK,msg = None,**kwargs):
        self.code = code
        self.msg = msg
        self.rdict = dict(**kwargs)
    def __setattr__(self,k,v):
        if k == "code":
            if isinstance(v,int):
                self.__dict__["code"] = v
            elif isinstance(v,RC):
                self.__dict__["code"] = v.value
            else:
                raise Exception("bad code type")
        elif k == "msg":
            if v == None or isinstance(v,str) or isinstance(v,bytes):
                self.__dict__["msg"] = v
            else:
                raise Exception("bad msg type")
        else:
            self.__dict__[k] = v
    def __getattr__(self,k):
        return self.__dict__[k]
    def __str__(self):
        ret = {
        "code":self.code,
        "msg":self.msg,
        }
        if not self.msg :
            ret = {"code":self.code,}
        ret.update(self.rdict)
        print(ret)
        return json.dumps(ret)
    def __repr__(self):
        try:
            return "<JsonResponse \"%s\">" % self.__str__()
        except e:
            return "<JsonResponse malform:%s>" % str(e)

# exception handlers
@app.errorhandler(500)
def all_exception_handler(e):
    return e.description or str(JsonResponse(RC.IntErr,"svr int err")), 500

@app.errorhandler(400)
def bad_req(e):
    return e.description or str(JsonResponse(RC.BadReq,"bad request")), 400

@app.errorhandler(404)
def not_found(e):
    return e.description or str(JsonResponse(RC.NotFound,"not found")), 404

@app.errorhandler(403)
def bad_auth(e):
    return e.description or str(JsonResponse(RC.AuthFail,"auth fail")), 403

# opearation to canvas
@app.route("/<path:cid>",methods=['GET', 'POST', 'PUT', 'UPDATE'])
def pcanvas(cid):
    credis = getattr(current_app, '_credis', None)
    if credis is None:
        credis = current_app._credis = redis.StrictRedis(host=redis_host, port=redis_port, db=0)
    canvas = getattr(current_app, '_canvas', None)
    if canvas is None:
        #first load: read from redis
        canvas = current_app._canvas = {}
        ks = credis.keys("*")
        for k in ks:
            #print("got",k,credis.get(k))
            canvas[k.decode("utf8")] = HilbertCanvas(0,credis.get(k).decode("ascii"))
    #print(canvas)
    if request.method == "GET":
        #print(canvas.keys())
        if not  cid in canvas.keys():
            abort(404,str(JsonResponse(RC.NotFound,"not found")))
        return str(JsonResponse(RC.OK,data=canvas[cid].data))
    elif request.method == "POST":
        #print(pyotp.TOTP('CAFEBABEDEADBEEF').now(),request.headers.get("Iam-UR-Father"))
        if request.headers.get("Iam-UR-Father") == "123456":#pyotp.TOTP('CAFEBABEDEADBEEF').now():
            if not cid in canvas.keys():
                #print(canvas)
                level = request.form.getlist("level")
                if len(level)>0:
                    level = int(level[0])
                else:
                    level = 3
                canvas[cid] = HilbertCanvas(level)
                # save to redis
                credis.set(cid, canvas[cid].data)
                #print(canvas)
            return str(JsonResponse(RC.OK))
        else:
            abort(403,str(JsonResponse(RC.AuthFail,"not auth")))
    elif request.method == "UPDATE":
        #print(pyotp.TOTP('CAFEBABEDEADBEEF').now(),request.headers.get("Iam-UR-Father"))
        if request.headers.get("Iam-UR-Father") == "123456":#pyotp.TOTP('CAFEBABEDEADBEEF').now():
            if not cid in canvas.keys():
                abort(404,str(JsonResponse(RC.NotFound,"no such cid")))
            #print(cid)
            canvas[cid].update()
            # save to redis
            credis.set(cid, canvas[cid].data)
            return str(JsonResponse(RC.OK,"ok"))
        else:
            abort(403,str(JsonResponse(RC.AuthFail,"not auth")))

# pixel operation indexed by (x,y), should be disabled
#@app.route("/<path:cid>/<int:x>/<int:y>",methods=['PUT'])
def canvaspixelxy(cid,x,y):
        canvas = getattr(current_app, '_canvas', None)
        if canvas is None:
            abort(404,str(JsonResponse(RC.NotFound,"not found")))
        #print(canvas.keys())
        if not cid in canvas.keys():
            abort(404,str(JsonResponse(RC.NotFound,"not found")))
        hc = canvas[cid]
        try:
            c = request.form.getlist("c")[0]
        except:
            abort(400,str(JsonResponse(RC.BadReq,"bad argument c")))
        try:
            hc.set(x,y,str(c))
        except Exception as e:
            print(e)
            abort(400,str(JsonResponse(RC.BadReq,"bad color")))
        return str(JsonResponse(RC.OK,"done"))

# pixel operation indexed by n
@app.route("/<path:cid>/<int:n>",methods=['GET','PUT'])
def canvaspixeln(cid,n):
        canvas = getattr(current_app, '_canvas', None)
        if canvas is None:
            abort(404,str(JsonResponse(RC.NotFound,"not found")))
        #print(canvas.keys())
        credis = getattr(current_app, '_credis', None)
        if credis is None:
            abort(500,str(JsonResponse(RC.IntErr,"not prepared")))
        if not cid in canvas.keys():
            abort(404,str(JsonResponse(RC.NotFound,"not found")))
        hc = canvas[cid]
        if request.method == "GET":
            return str(JsonResponse(RC.OK,data=hc.getn(n)))
        try:
            c = request.form.getlist("c")[0]
        except:
            abort(400,str(JsonResponse(RC.BadReq,"bad argument c")))
        try:
            hc.setn(n,str(c))
            credis.set(cid, hc.data)
        except Exception as e:
            print(e)
            abort(400,str(JsonResponse(RC.BadReq,"bad color")))
        return str(JsonResponse(RC.OK,"done"))

# static demo
@app.route("/statictest/<path:cid>.html")
def statictest(cid):
    canvas = getattr(current_app, '_canvas', None)
    if canvas is None:
        abort(404)
    return render_template('template.html',cid=cid, data = canvas[cid].data)

# packet type used in websocket
class PackType(Enum):
    REFRESH = 0xcafe
    PUT = 0xbabe
    GET = 0xdead # should not be implemented
    POST = 0x706f # do not use this
    INFO = 0xbeef

    ERROR = 0x6e6f
    OK = 0x6f6b

def unpack_msg(msg):
    #try:
    size = struct.unpack(">I",msg[0:4])[0]
    #print(size,len(msg))
    if not size + 6 == len(msg):
        return PackType.ERROR, b''
    try:
        pkttype = PackType(struct.unpack(">H",msg[4:6])[0])
        #print(pkttype)
    except:
        return PackType.ERROR, b''
    return pkttype, msg[6:]

def pack_msg(head,payload:bytes):
    return struct.pack(">I",len(payload)) + struct.pack(">H",head.value) + payload

def auth(uid,token):
    print(uid,token)

    aredis = getattr(current_app, '_aredis', None)
    if not aredis:
        aredis = current_app._aredis = redis.StrictRedis(host=redis_host, port=redis_port, db=1)

    hard_token = struct.pack(">I",uid)+token
    # hard_token : 4byte uid | 20byte tokenl | 4byte tokens
    ok = aredis.get(hard_token)
    if ok :
        print("aredis cached token",ok)
        return True
    else:
        print("no token, regen")
        if ext_auth(uid,token):
            aredis.set(hard_token,True)
            aredis.expire(hard_token,600)
            return True
        else:
            return False

def colddown(uid):
    #return True
    dredis = getattr(current_app, '_dredis', None)
    if not dredis:
        dredis = current_app._dredis = redis.StrictRedis(host=redis_host, port=redis_port, db=2)

    ok = int(dredis.get(uid) or "0") or 0
    if ok == 0 :
        dredis.set(uid,"1")
        dredis.expire(uid,cdt)
        return True
    elif ok < 10:
        dredis.set(uid,"%d" % (ok+1))
        dredis.expire(uid,cdt)
        return False
    else :
        dredis.set(uid,"%d" % (ok+1))
        dredis.expire(uid,cdt*10)
        return False

def colddown_get(uid):
    if not uid:
        return 0
    dredis = getattr(current_app, '_dredis', None)
    if not dredis:
        dredis = current_app._dredis = redis.StrictRedis(host=redis_host, port=redis_port, db=2)

    recorded = dredis.get(uid)
    if not recorded or dredis.ttl(uid) == -2:
        return 0
    else:
        return dredis.ttl(uid)

def setn(cid,n,c):
    credis = getattr(current_app, '_credis', None)
    if credis is None:
        credis = current_app._credis = redis.StrictRedis(host=redis_host, port=redis_port, db=0)
    canvas = getattr(current_app, '_canvas', None)
    if canvas is None:
        #first load: read from redis
        canvas = current_app._canvas = {}
        ks = credis.keys("*")
        for k in ks:
            #print("got",k,credis.get(k))
            canvas[k.decode("utf8")] = HilbertCanvas(0,credis.get(k).decode("ascii"))
    target = canvas.get(cid)
    if not target:
        raise Exception("no such cid")
    target.setn(n,c)
    credis.set(cid, target.data)

def notify_all(t):
    wslist = getattr(current_app, '_wslist', None)
    can = getattr(current_app, '_canvas', None)
    for ws in wslist[t]:
        if not ws[0].closed:
            ws[0].send(pack_msg(PackType.OK,b64.b32decode(can[t].data)))
        else:
            del ws

def inform_all():
    wslist = getattr(current_app, '_wslist', None)
    can = getattr(current_app, '_canvas', None)
    for t in wslist.keys():
        online = len(wslist[t])
        for ws in wslist[t]:
            if not ws[0].closed:
                ws[0].send(pack_msg(PackType.INFO,struct.pack(">I",online)+struct.pack(">I",colddown_get(ws[1]))))
            else:
                del ws

@sockets.route('/ws')
def websock(ws):
    wslist = getattr(current_app, '_wslist', None)
    if wslist is None:
        wslist = current_app._wslist = {}
    while not ws.closed:
        try:
            message = bytes(ws.receive())
        except:
            if not ws.closed:
                ws.close()
        try:
            head, body = unpack_msg(message)
            if head == PackType.REFRESH: # refresh data
                can = getattr(current_app, '_canvas', None)
                cid = body.decode()
                t = can.get(cid)
                if not can or not t:
                    ws.send(pack_msg(PackType.ERROR,b"no such cid"))
                    continue

                if not wslist.get(cid):
                    wslist[cid] = []

                wslist[cid].append((ws,None))
                ws.send(pack_msg(PackType.OK,b64.b32decode(t.data)))
                ws.send(pack_msg(PackType.INFO,struct.pack(">I",len(wslist[cid]))+struct.pack(">I",colddown_get(None))))
            elif head == PackType.PUT :
                # 4byte size | 2byte pkttype | 4byte n | byte color | hard_token 28bytes | xbytes cid
                # 0            4               6         10           11                   39
                can = getattr(current_app, '_canvas', None)
                n = struct.unpack(">I",body[0:4])[0]
                c = body[4]
                hard_token = body[5:33]
                cid = body[33:].decode()
                t = can.get(cid)

                #print(n,c,hard_token,t)

                if not can or not t:
                    ws.send(pack_msg(PackType.ERROR,b"no such cid"))
                    continue

                if not wslist.get(cid):
                    wslist[cid] = []

                uid = struct.unpack(">I",hard_token[0:4])[0]
                wslist[cid].append((ws,uid))

                if auth(uid,hard_token[4:]):
                    if colddown(uid):
                        t.setn(n,chr(c))
                        notify_all(cid)
                        ws.send(pack_msg(PackType.OK,b64.b32decode(t.data)))
                    else:
                        #print(auth(uid,hard_token[4:]),colddown(uid))
                        ws.send(pack_msg(PackType.ERROR,b"colding down"))
                        ws.send(pack_msg(PackType.INFO,struct.pack(">I",len(wslist[cid]))+struct.pack(">I",colddown_get(uid))))
                else:
                    #print(auth(uid,hard_token[4:]),colddown(uid))
                    ws.send(pack_msg(PackType.ERROR,b"not auth"))
            elif head == PackType.ERROR :
                ws.send(pack_msg(PackType.ERROR,b"bad request"))
                ws.close()
        except Exception as e:
            if not ws.closed:
                ws.send(pack_msg(PackType.ERROR,b"int err"))
                ws.close()
            raise e

if __name__ == "__main__":
    if sys.argv[1] == "run":
        from gevent import pywsgi
        from geventwebsocket.handler import WebSocketHandler
        server = pywsgi.WSGIServer(('0.0.0.0', 5000), app, handler_class=WebSocketHandler)
        server.serve_forever()
    elif sys.argv[1] == "dumph":
        print("todo")
    else:
        os.system(" ".join(sys.argv[1:]))
