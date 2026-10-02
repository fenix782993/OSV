import os, sqlite3, hashlib, hmac, secrets, json, time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT=Path(__file__).parent
DB=ROOT/"osv.db"
app=FastAPI(title="ОСВ — Аттестация", version="1.0.0")
app.mount("/static", StaticFiles(directory=ROOT/"static"), name="static")
SECRET=os.getenv("APP_SECRET", "change-this-secret-on-render").encode()
OWNER="Fenix_Dinero"

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, nickname TEXT UNIQUE NOT NULL,
      position TEXT NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'Кандидат',
      created INTEGER NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS questions(
      id INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT NOT NULL, options TEXT NOT NULL,
      correct INTEGER NOT NULL, points INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS attempts(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, score INTEGER NOT NULL,
      total INTEGER NOT NULL, passed INTEGER NOT NULL, answers TEXT NOT NULL, created INTEGER NOT NULL)""")
    c.commit(); return c
def pw_hash(p,s=None):
    s=s or secrets.token_hex(16)
    return s+"$"+hashlib.pbkdf2_hmac("sha256",p.encode(),s.encode(),180000).hex()
def check_pw(p,stored):
    try:
        s,v=stored.split("$",1)
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256",p.encode(),s.encode(),180000).hex(),v)
    except: return False
def token(uid):
    raw=f"{uid}:{int(time.time())+86400*14}"
    sig=hmac.new(SECRET,raw.encode(),hashlib.sha256).hexdigest()
    return raw+"."+sig
def current(req):
    t=req.cookies.get("osv_session","")
    try:
        raw,sig=t.rsplit(".",1)
        if not hmac.compare_digest(sig,hmac.new(SECRET,raw.encode(),hashlib.sha256).hexdigest()): return None
        uid,exp=raw.split(":")
        if int(exp)<time.time(): return None
        c=db(); u=c.execute("SELECT * FROM users WHERE id=?",(int(uid),)).fetchone(); c.close()
        return u
    except: return None
def require(req,staff=False):
    u=current(req)
    if not u: raise HTTPException(401,"Войдите в аккаунт")
    if staff and u["role"] not in ("Владелец","Инструктор"): raise HTTPException(403,"Недостаточно прав")
    return u
class Register(BaseModel):
    nickname:str=Field(min_length=3,max_length=32)
    position:str=Field(min_length=2,max_length=60)
    password:str=Field(min_length=6,max_length=100)
class Login(BaseModel):
    nickname:str
    password:str
class QuestionIn(BaseModel):
    body:str=Field(min_length=3,max_length=700)
    options:list[str]
    correct:int
    points:int=Field(ge=0,le=33)
    active:bool=True
class Answers(BaseModel):
    answers:dict[str,int]
class RoleIn(BaseModel):
    role:str
@app.on_event("startup")
def startup():
    c=db()
    owner=c.execute("SELECT id FROM users WHERE nickname=?",(OWNER,)).fetchone()
    if not owner:
        c.execute("INSERT INTO users(nickname,position,password,role,created) VALUES(?,?,?,?,?)",
          (OWNER,"Инструктор ОСВ",pw_hash(os.getenv("OWNER_PASSWORD","ChangeMe_123!")),"Владелец",int(time.time())))
    c.commit(); c.close()
@app.get("/")
def index(): return FileResponse(ROOT/"static/index.html")
@app.get("/api/health")
def health(): return {"status":"online","service":"OSV Attestation"}
@app.post("/api/register")
def register(x:Register,response:Response):
    c=db()
    try:
        cur=c.execute("INSERT INTO users(nickname,position,password,role,created) VALUES(?,?,?,?,?)",
          (x.nickname.strip(),x.position.strip(),pw_hash(x.password),"Кандидат",int(time.time())))
        c.commit(); uid=cur.lastrowid
    except sqlite3.IntegrityError:
        c.close(); raise HTTPException(409,"Такой игровой ник уже зарегистрирован")
    c.close(); response.set_cookie("osv_session",token(uid),httponly=True,samesite="lax",secure=os.getenv("COOKIE_SECURE","0")=="1",max_age=1209600)
    return {"ok":True}
@app.post("/api/login")
def login(x:Login,response:Response):
    c=db(); u=c.execute("SELECT * FROM users WHERE nickname=?",(x.nickname.strip(),)).fetchone(); c.close()
    if not u or not check_pw(x.password,u["password"]): raise HTTPException(401,"Неверный ник или пароль")
    response.set_cookie("osv_session",token(u["id"]),httponly=True,samesite="lax",secure=os.getenv("COOKIE_SECURE","0")=="1",max_age=1209600)
    return {"ok":True}
@app.post("/api/logout")
def logout(response:Response):
    response.delete_cookie("osv_session"); return {"ok":True}
@app.get("/api/me")
def me(req:Request):
    u=current(req)
    if not u:return {"user":None}
    return {"user":{"id":u["id"],"nickname":u["nickname"],"position":u["position"],"role":u["role"]}}
@app.get("/api/roster")
def roster():
    c=db(); rows=c.execute("SELECT id,nickname,position,role,created FROM users ORDER BY CASE role WHEN 'Владелец' THEN 0 WHEN 'Начальник ОСВ' THEN 1 WHEN 'Заместитель начальника ОСВ' THEN 2 WHEN 'Старший инспектор' THEN 3 WHEN 'Инспектор' THEN 4 WHEN 'Инструктор' THEN 5 WHEN 'Стажёр' THEN 6 ELSE 7 END,nickname COLLATE NOCASE").fetchall(); c.close()
    return [dict(r) for r in rows]
@app.get("/api/questions")
def questions(req:Request):
    u=current(req); c=db()
    rows=c.execute("SELECT id,body,options,points FROM questions WHERE active=1 ORDER BY id").fetchall()
    c.close()
    return [{"id":r["id"],"body":r["body"],"options":json.loads(r["options"]),"points":r["points"]} for r in rows]
@app.get("/api/admin/questions")
def admin_questions(req:Request):
    require(req,True); c=db(); rows=c.execute("SELECT * FROM questions ORDER BY id").fetchall(); c.close()
    return [{"id":r["id"],"body":r["body"],"options":json.loads(r["options"]),"correct":r["correct"],"points":r["points"],"active":bool(r["active"])} for r in rows]
@app.post("/api/admin/questions")
def add_question(x:QuestionIn,req:Request):
    require(req,True)
    if len(x.options)<2 or len(x.options)>6 or any(not a.strip() for a in x.options) or x.correct<0 or x.correct>=len(x.options): raise HTTPException(400,"Добавьте 2–6 вариантов и укажите правильный")
    c=db(); count=c.execute("SELECT COUNT(*) n FROM questions").fetchone()["n"]
    if count>=33:c.close();raise HTTPException(400,"В аттестации может быть не более 33 вопросов")
    cur=c.execute("INSERT INTO questions(body,options,correct,points,active) VALUES(?,?,?,?,?)",(x.body.strip(),json.dumps(x.options,ensure_ascii=False),x.correct,x.points,int(x.active)));c.commit();qid=cur.lastrowid;c.close();return {"id":qid}
@app.put("/api/admin/questions/{qid}")
def edit_question(qid:int,x:QuestionIn,req:Request):
    require(req,True)
    if len(x.options)<2 or len(x.options)>6 or x.correct<0 or x.correct>=len(x.options):raise HTTPException(400,"Проверьте варианты ответа")
    c=db(); cur=c.execute("UPDATE questions SET body=?,options=?,correct=?,points=?,active=? WHERE id=?",(x.body.strip(),json.dumps(x.options,ensure_ascii=False),x.correct,x.points,int(x.active),qid));c.commit();c.close()
    if not cur.rowcount:raise HTTPException(404,"Вопрос не найден")
    return {"ok":True}
@app.delete("/api/admin/questions/{qid}")
def delete_question(qid:int,req:Request):
    require(req,True);c=db();c.execute("DELETE FROM questions WHERE id=?",(qid,));c.commit();c.close();return {"ok":True}
@app.get("/api/admin/users")
def admin_users(req:Request):
    require(req,True);c=db();rows=c.execute("SELECT id,nickname,position,role,created FROM users ORDER BY nickname").fetchall();c.close();return [dict(r) for r in rows]
@app.patch("/api/admin/users/{uid}/role")
def set_role(uid:int,x:RoleIn,req:Request):
    actor=require(req,True)
    allowed=["Кандидат","Начальник ОСВ","Заместитель начальника ОСВ","Стажёр","Инструктор","Инспектор","Старший инспектор"]
    if x.role not in allowed:raise HTTPException(400,"Недопустимая должность")
    if actor["role"]!="Владелец":raise HTTPException(403,"Назначать должности может только владелец")
    c=db();c.execute("UPDATE users SET role=? WHERE id=? AND nickname<>?",(x.role,uid,OWNER));c.commit();c.close();return {"ok":True}
@app.post("/api/submit")
def submit(x:Answers,req:Request):
    u=require(req);c=db();qs=c.execute("SELECT id,correct,points FROM questions WHERE active=1 ORDER BY id").fetchall()
    if len(qs)!=33:c.close();raise HTTPException(400,f"Аттестация пока не готова: активных вопросов {len(qs)} из 33")
    if len(x.answers)!=33:c.close();raise HTTPException(400,"Ответьте на все 33 вопроса")
    score=0; detail={}
    for q in qs:
        val=x.answers.get(str(q["id"]))
        if val is None or val<0:c.close();raise HTTPException(400,"Ответьте на все вопросы")
        ok=val==q["correct"]
        if ok:score+=q["points"]
        detail[str(q["id"])]={"selected":val,"correct":q["correct"],"ok":ok}
    total=sum(q["points"] for q in qs); passed=score>=28 and total>=28
    c.execute("INSERT INTO attempts(user_id,score,total,passed,answers,created) VALUES(?,?,?,?,?,?)",(u["id"],score,total,int(passed),json.dumps(detail),int(time.time())))
    c.commit();c.close()
    return {"score":score,"total":total,"passed":passed,"contact":"karl_limansky2025"}
@app.get("/api/admin/results")
def results(req:Request):
    require(req,True);c=db();rows=c.execute("SELECT a.*,u.nickname,u.position FROM attempts a JOIN users u ON u.id=a.user_id ORDER BY a.created DESC LIMIT 200").fetchall();c.close()
    return [{"nickname":r["nickname"],"position":r["position"],"score":r["score"],"total":r["total"],"passed":bool(r["passed"]),"created":r["created"]} for r in rows]
