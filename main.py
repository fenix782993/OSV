import os, sqlite3, hashlib, hmac, secrets, json, time, re
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
ROOT=Path(__file__).resolve().parent; DB=Path(os.getenv("DB_PATH",str(ROOT/"osv.db"))); DB.parent.mkdir(parents=True,exist_ok=True)
app=FastAPI(title="ОСВ — Аттестация",version="2.0.0")
app.mount("/static",StaticFiles(directory=ROOT/"static"),name="static")
SECRET=os.getenv("APP_SECRET","change-this-secret-on-render").encode(); OWNER="Fenix_Dinero"; PASS_SCORE=28; QUESTION_COUNT=33; EXAM_LIMIT_SECONDS=30*60
ROLES=["Начальник ОСВ","Заместитель начальника ОСВ","Стажёр","Старший инспектор","Инспектор","Инструктор","Администратор"]
RANKS=["Без звания","Полковник","Генерал"]
QUESTION_BANK = [
"На каком основании снимать маску с задержанного?",
"В каком случае можно одеть мешок на голову задержанного и на каком основании?",
"Что такое диспозиция в УК?",
"С какого звания можно задержать своего сотрудника?",
"Виды мед.помощи.",
"Может ли инспектор ОСВ проводить ОПМ, ОРД и на каком основании?",
"Что запрещено делать во время переговоров?",
"Можно ли обезвредить пояс смертника на человеке?",
"Основание на задержание сотрудника МВД?",
"Какие есть виды оружия?",
"В каких случаях можно открыть огонь в городе?",
"Что будете делать, если сотрудник употребит мятную пудру?",
"С какого момента начинается уголовное преследование?",
"При каких обстоятельствах можно применить спецсредства, какие требования должны быть соблюдены перед их применением?",
"На каком основании вы можете задержать сотрудника?",
"С какого звания можно задерживать сотрудников МВД?",
"На каком основании вы можете изъять лицензии на оружие и на права?",
"На каком основании вы будете требовать покинуть граждан место проведения задержания или других различных мероприятий?",
"На каком основании человек имеет право на жизнь? (Конституция)",
"Основание на задержание находящегося лица в розыске.",
"На каком основании задержанный имеет право на адвоката? (Конституция)",
"Ваши первые действия при переговорах?",
"Чем отличается 67 УК от 20.5 КоАП?",
"Ваши действия, если при проверке документов у гражданина не стоит дата рождения?",
"На каком основании вы будете замерять и снимать тонировку?",
"О чем гласит 12.5 ВУ?",
"Что вы сделаете, если увидите гражданина на парковке ГИБДД?",
"О чем гласит 4.3 ВУ?",
"Как правильно должен представляться инспектор ОСВ?",
"Как правильно обращаться к руководству УГИБДД?",
"Основные задачи ОСВ.",
"Иерархия Федеральных законов?",
"Кто подчиняется ОСВ?"
]

def db():
 c=sqlite3.connect(DB,timeout=20); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON")
 c.executescript("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,nickname TEXT UNIQUE NOT NULL,mask TEXT NOT NULL DEFAULT '',position TEXT NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'Стажёр',created INTEGER NOT NULL,role_approved INTEGER NOT NULL DEFAULT 0,last_login INTEGER,role_requested TEXT,rank TEXT NOT NULL DEFAULT 'Без звания',retake_required INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY AUTOINCREMENT,body TEXT NOT NULL,options TEXT NOT NULL,correct INTEGER NOT NULL,points INTEGER NOT NULL DEFAULT 1,active INTEGER NOT NULL DEFAULT 1); CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,score INTEGER NOT NULL DEFAULT 0,total INTEGER NOT NULL DEFAULT 33,passed INTEGER NOT NULL DEFAULT 0,answers TEXT NOT NULL DEFAULT '{}',created INTEGER NOT NULL,started INTEGER,finished INTEGER,status TEXT NOT NULL DEFAULT 'started',FOREIGN KEY(user_id) REFERENCES users(id)); CREATE TABLE IF NOT EXISTS exam_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created INTEGER NOT NULL,reviewed INTEGER,reviewed_by TEXT,FOREIGN KEY(user_id) REFERENCES users(id)); CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,nickname TEXT NOT NULL,event TEXT NOT NULL,details TEXT NOT NULL DEFAULT '',created INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS attempt_questions(attempt_id INTEGER NOT NULL,question_id INTEGER NOT NULL,body_snapshot TEXT NOT NULL,answer TEXT NOT NULL DEFAULT '',mark INTEGER,reviewed_by TEXT,reviewed_at INTEGER,PRIMARY KEY(attempt_id,question_id),FOREIGN KEY(attempt_id) REFERENCES attempts(id)); CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,created INTEGER NOT NULL,seen INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS personnel_notes(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,kind TEXT NOT NULL,body TEXT NOT NULL,actor TEXT NOT NULL,created INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS chat_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,room TEXT NOT NULL,sender_id INTEGER NOT NULL,recipient_id INTEGER,body TEXT NOT NULL,created INTEGER NOT NULL,FOREIGN KEY(sender_id) REFERENCES users(id),FOREIGN KEY(recipient_id) REFERENCES users(id)); CREATE TABLE IF NOT EXISTS user_history(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,actor TEXT NOT NULL,field TEXT NOT NULL,old_value TEXT,new_value TEXT,created INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS user_permissions(user_id INTEGER PRIMARY KEY,permissions TEXT NOT NULL DEFAULT '[]'); CREATE TABLE IF NOT EXISTS app_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);")
 # additive migrations for existing databases
 cols={r['name'] for r in c.execute('PRAGMA table_info(users)')}
 for name,ddl in [('role_approved','INTEGER NOT NULL DEFAULT 0'),('last_login','INTEGER'),('role_requested','TEXT'),('rank',"TEXT NOT NULL DEFAULT 'Без звания'"),('retake_required','INTEGER NOT NULL DEFAULT 0')]:
  if name not in cols: c.execute(f'ALTER TABLE users ADD COLUMN {name} {ddl}')
 c.execute("UPDATE users SET role_requested=position WHERE role_approved=0 AND (role_requested IS NULL OR role_requested='') AND position IN ('Начальник ОСВ','Заместитель начальника ОСВ','Инструктор','Старший инспектор','Инспектор','Стажёр')")
 acols={r['name'] for r in c.execute('PRAGMA table_info(attempts)')}
 for name,ddl in [('started','INTEGER'),('finished','INTEGER'),('status',"TEXT NOT NULL DEFAULT 'started'")]:
  if name not in acols: c.execute(f'ALTER TABLE attempts ADD COLUMN {name} {ddl}')
 c.commit(); return c
def audit(c,u,event,details=''):
 c.execute('INSERT INTO audit(user_id,nickname,event,details,created) VALUES(?,?,?,?,?)',(u['id'] if u else None,u['nickname'] if u else 'system',event,details,int(time.time())))
def delete_user_data(c, uid):
 c.execute('DELETE FROM exam_requests WHERE user_id=?',(uid,))
 c.execute('DELETE FROM attempt_questions WHERE attempt_id IN (SELECT id FROM attempts WHERE user_id=?)',(uid,))
 c.execute('DELETE FROM notifications WHERE user_id=?',(uid,))
 c.execute('DELETE FROM personnel_notes WHERE user_id=?',(uid,))
 c.execute('DELETE FROM attempts WHERE user_id=?',(uid,))
 c.execute('DELETE FROM user_history WHERE user_id=?',(uid,))
 c.execute('DELETE FROM user_permissions WHERE user_id=?',(uid,))
 c.execute('DELETE FROM chat_messages WHERE sender_id=? OR recipient_id=?',(uid,uid))
 c.execute('DELETE FROM users WHERE id=?',(uid,))
def pw_hash(p,s=None):
 s=s or secrets.token_hex(16); return s+'$'+hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),180000).hex()
def check_pw(p,stored):
 try:
  s,v=stored.split('$',1); return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),180000).hex(),v)
 except Exception:return False
def token(uid):
 raw=f"{uid}:{int(time.time())+1209600}"; sig=hmac.new(SECRET,raw.encode(),hashlib.sha256).hexdigest(); return raw+'.'+sig
def current(req):
 try:
  raw,sig=req.cookies.get('osv_session','').rsplit('.',1); exp_sig=hmac.new(SECRET,raw.encode(),hashlib.sha256).hexdigest()
  if not hmac.compare_digest(sig,exp_sig):return None
  uid,exp=raw.split(':');
  if int(exp)<time.time():return None
  c=db(); u=c.execute('SELECT * FROM users WHERE id=?',(int(uid),)).fetchone(); c.close(); return u
 except Exception:return None
def require(req,staff=False,owner=False):
 u=current(req)
 if not u: raise HTTPException(401,'Войдите в аккаунт')
 if staff and (u['role'] not in ('Владелец','Инструктор','Начальник ОСВ','Заместитель начальника ОСВ','Администратор') or (u['role']!='Владелец' and not u['role_approved'])):raise HTTPException(403,'Недостаточно прав или должность не подтверждена')
 if owner and u['role'] not in ('Владелец','Начальник ОСВ'):raise HTTPException(403,'Недостаточно прав: требуется владелец или начальник ОСВ')
 return u
def require_staff_action(req):
 u=require(req,staff=True)
 if u['role']=='Администратор': raise HTTPException(403,'Администратор имеет доступ только на просмотр и контроль')
 return u
def is_admin(u): return u and u['role']=='Администратор'
class Register(BaseModel): nickname:str=Field(min_length=3,max_length=32); mask:str=Field(min_length=1,max_length=32); position:str=Field(min_length=2,max_length=60); password:str=Field(min_length=6,max_length=100)
class Login(BaseModel): nickname:str; password:str
class QuestionIn(BaseModel): body:str=Field(min_length=3,max_length=700); options:list[str]; correct:int; points:int=Field(default=1,ge=1,le=1); active:bool=True
class Answers(BaseModel): answers:dict[str,str]
class RoleIn(BaseModel): role:str
class MaskIn(BaseModel): mask:str=Field(min_length=1,max_length=32)
class AnswerSave(BaseModel): question_id:int; answer:str=Field(default='',max_length=10000)

def validate_question(x: QuestionIn):
 if not x.body.strip(): raise HTTPException(400, 'Введите текст вопроса')
 # Written-response questions intentionally have no answer options.
 if x.options and len(x.options) != 4: raise HTTPException(400, 'Для тестового вопроса нужно ровно 4 варианта')
 if x.options and any(not isinstance(o, str) or not o.strip() or len(o) > 300 for o in x.options): raise HTTPException(400, 'Каждый вариант должен содержать 1–300 символов')
 if x.options and x.correct not in range(4): raise HTTPException(400, 'Правильный ответ должен быть от 0 до 3')
 if not x.options and x.correct != -1: raise HTTPException(400, 'Письменный вопрос не имеет правильного варианта')
@app.on_event('startup')
def startup():
 c=db()
 seeded=c.execute("SELECT value FROM app_meta WHERE key='written_question_bank_v1'").fetchone()
 if not seeded:
  # One-time migration: deactivate the old demo bank and add the requested 33 written questions without breaking existing attempt history.
  c.execute('UPDATE questions SET active=0')
  for body in QUESTION_BANK:
   c.execute('INSERT INTO questions(body,options,correct,points,active) VALUES(?,"[]",-1,1,1)',(body,))
  c.execute("INSERT INTO app_meta(key,value) VALUES('written_question_bank_v1','1')")
 owner=c.execute('SELECT * FROM users WHERE nickname=?',(OWNER,)).fetchone()
 if not owner:c.execute('INSERT INTO users(nickname,position,password,role,created,role_approved,role_requested) VALUES(?,?,?,?,?,1,?)',(OWNER,'Владелец ОСВ',pw_hash(os.getenv('OWNER_PASSWORD','ChangeMe_123!')),'Владелец',int(time.time()),'Владелец'))
 else:c.execute("UPDATE users SET role='Владелец',role_approved=1,role_requested='Владелец' WHERE nickname=?",(OWNER,))
 c.commit();c.close()
@app.get('/')
def index():return FileResponse(ROOT/'static'/'index.html')
@app.get('/banner.jpg')
def banner():
 p=ROOT/'banner.jpg'
 if not p.exists():raise HTTPException(404,'Баннер не загружен')
 return FileResponse(p,media_type='image/jpeg')
@app.get('/api/health')
def health():
 c=db(); users=c.execute('SELECT COUNT(*) FROM users').fetchone()[0]; c.close(); return {'status':'online','service':'OSV Attestation','database':'sqlite','users':users}
def user_dict(u):return {'id':u['id'],'nickname':u['nickname'],'mask':u['mask'] if 'mask' in u.keys() else '','position':u['position'],'role':u['role'],'role_approved':bool(u['role_approved']),'role_requested':u['role_requested'],'last_login':u['last_login'],'rank':u['rank'] if 'rank' in u.keys() else 'Без звания','retake_required':bool(u['retake_required']) if 'retake_required' in u.keys() else False}
@app.post('/api/register')
def register(x:Register,response:Response):
 nick=x.nickname.strip(); mask=x.mask.strip(); role=x.position.strip()
 if role not in ROLES or role=='Администратор': raise HTTPException(400,'Выберите корректную должность')
 if role=='Стажёр': role='Стажёр'
 if not mask.isdigit(): raise HTTPException(400,'Маска должна содержать только цифры')
 if role not in ROLES:raise HTTPException(400,'Выберите должность из списка')
 c=db()
 try:
  cur=c.execute("INSERT INTO users(nickname,mask,position,password,role,created,role_approved,role_requested) VALUES(?,?,?,?,?,?,0,?)",(nick,x.mask.strip(),role,pw_hash(x.password),'Стажёр',int(time.time()),role)); uid=cur.lastrowid
  u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone();audit(c,u,'Регистрация',f'Заявлена должность: {role}');c.execute('INSERT INTO user_history(user_id,actor,field,old_value,new_value,created) VALUES(?,?,?,?,?,?)',(uid,nick,'Заявленная должность','',role,int(time.time())));now=int(time.time());
  for manager in c.execute("SELECT id FROM users WHERE role IN ('Владелец','Начальник ОСВ','Заместитель начальника ОСВ') AND role_approved=1").fetchall():c.execute('INSERT INTO notifications(user_id,title,body,created) VALUES(?,?,?,?)',(manager['id'],'Новая регистрация',f'{nick} подал заявку на вступление',now))
  c.commit()
 except sqlite3.IntegrityError:c.close();raise HTTPException(409,'Такой игровой ник уже зарегистрирован')
 c.close();return {'ok':True,'user_id':uid,'message':'Регистрация успешна. Выполните вход.'}
@app.post('/api/login')
def login(x:Login,response:Response):
 c=db();u=c.execute('SELECT * FROM users WHERE nickname=?',(x.nickname.strip(),)).fetchone()
 if not u or not check_pw(x.password,u['password']):c.close();raise HTTPException(401,'Неверный ник или пароль')
 now=int(time.time());c.execute('UPDATE users SET last_login=? WHERE id=?',(now,u['id']));u=c.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone();audit(c,u,'Вход на сайт');c.commit();c.close();response.set_cookie('osv_session',token(u['id']),httponly=True,samesite='lax',secure=os.getenv('COOKIE_SECURE','0')=='1',max_age=1209600);return {'ok':True}
@app.post('/api/logout')
def logout(req:Request,response:Response):
 u=current(req)
 if u:
  c=db();audit(c,u,'Выход с сайта');c.commit();c.close()
 response.delete_cookie('osv_session');return {'ok':True}
@app.get('/api/me')
def me(req:Request):
 u=current(req)
 if not u:return {'user':None}
 c=db();now=int(time.time());c.execute('UPDATE users SET last_login=COALESCE(last_login,?) WHERE id=?',(now,u['id']));u=c.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone();req_status=c.execute("SELECT status,created,reviewed FROM exam_requests WHERE user_id=? ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone();attempt=c.execute("SELECT id,started,finished,score,total,passed,status FROM attempts WHERE user_id=? ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone();c.close();return {'user':user_dict(u),'exam_request':dict(req_status) if req_status else None,'attempt':dict(attempt) if attempt else None}
@app.get('/api/roster')
def roster(req:Request):
 u=require(req);c=db();rows=c.execute("SELECT id,nickname,mask,position,role,rank,role_approved,created,last_login,role_requested,retake_required,(SELECT COUNT(*) FROM attempts a WHERE a.user_id=users.id) attempts_count,(SELECT score FROM attempts a WHERE a.user_id=users.id ORDER BY a.id DESC LIMIT 1) last_score,(SELECT total FROM attempts a WHERE a.user_id=users.id ORDER BY a.id DESC LIMIT 1) last_total,(SELECT passed FROM attempts a WHERE a.user_id=users.id ORDER BY a.id DESC LIMIT 1) last_passed,(SELECT status FROM attempts a WHERE a.user_id=users.id ORDER BY a.id DESC LIMIT 1) last_attempt_status FROM users WHERE role_approved=1 ORDER BY CASE role WHEN 'Владелец' THEN 0 WHEN 'Начальник ОСВ' THEN 1 WHEN 'Заместитель начальника ОСВ' THEN 2 WHEN 'Администратор' THEN 3 WHEN 'Старший инспектор' THEN 4 WHEN 'Инспектор' THEN 5 WHEN 'Инструктор' THEN 6 ELSE 7 END,nickname COLLATE NOCASE").fetchall();c.close();return [dict(r) for r in rows]
@app.post('/api/exam/request')
def exam_request(req:Request):
 u=require(req)
 if not u['role_approved']:raise HTTPException(403,'Сначала дождитесь подтверждения должности владельцем')
 if u['role']!='Стажёр':return {'ok':True,'status':'not_required'}
 c=db();old=c.execute("SELECT * FROM exam_requests WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone()
 if old:c.close();return {'ok':True,'status':'pending'}
 cur=c.execute("INSERT INTO exam_requests(user_id,status,created) VALUES(?,'pending',?)",(u['id'],int(time.time())));now=int(time.time());audit(c,u,'Заявка на аттестацию подана',f'Заявка №{cur.lastrowid}');
 for reviewer in c.execute("SELECT id FROM users WHERE role IN ('Владелец','Начальник ОСВ','Заместитель начальника ОСВ','Инструктор') AND role_approved=1").fetchall():c.execute('INSERT INTO notifications(user_id,title,body,created) VALUES(?,?,?,?)',(reviewer['id'],'Новая заявка на аттестацию',f'{u["nickname"]} подал заявку №{cur.lastrowid}',now))
 c.commit();c.close();return {'ok':True,'status':'pending'}
@app.post('/api/exam/start')
def start_exam(req: Request):
 u = require(req)
 if not u['role_approved']: raise HTTPException(403, 'Ваша должность ещё не подтверждена')
 c = db()
 try:
  if u['role'] != 'Стажёр' and not u['retake_required']:
   raise HTTPException(403, 'Аттестация доступна только стажёрам или сотрудникам, направленным на переаттестацию')
  if u['role'] == 'Стажёр':
   approval = c.execute("SELECT status FROM exam_requests WHERE user_id=? ORDER BY id DESC LIMIT 1", (u['id'],)).fetchone()
   if not approval or approval['status'] != 'approved': raise HTTPException(403, 'Сначала получите одобрение заявки на аттестацию')
  active = c.execute("SELECT * FROM attempts WHERE user_id=? AND status='started' ORDER BY id DESC LIMIT 1", (u['id'],)).fetchone()
  if active:
   if active['started'] and int(time.time())-active['started'] >= EXAM_LIMIT_SECONDS:
    now=int(time.time()); c.execute("UPDATE attempts SET status='expired',finished=? WHERE id=?",(now,active['id'])); audit(c,u,'Аттестация истекла',f'Попытка №{active["id"]} · превышен лимит 30 минут'); c.commit(); raise HTTPException(410,'Время аттестации истекло. Работа закрыта.')
   return {'ok': True, 'attempt_id': active['id'], 'status': 'started', 'resumed': True, 'started': active['started'], 'limit': EXAM_LIMIT_SECONDS}
  qs = c.execute("SELECT id,body,options FROM questions WHERE active=1 ORDER BY RANDOM() LIMIT ?", (QUESTION_COUNT,)).fetchall()
  if len(qs) < QUESTION_COUNT: raise HTTPException(400, f'Недостаточно активных вопросов: нужно {QUESTION_COUNT}, доступно {len(qs)}')
  now = int(time.time())
  cur = c.execute("INSERT INTO attempts(user_id,score,total,passed,answers,created,started,status) VALUES(?,0,33,0,'{}',?,?,'started')", (u['id'], now, now))
  aid = cur.lastrowid
  for q in qs:
   c.execute("INSERT INTO attempt_questions(attempt_id,question_id,body_snapshot,answer) VALUES(?,?,?,'')", (aid,q['id'],q['body']))
  audit(c,u,'Аттестация начата',f'Попытка №{aid} · лимит 30 минут')
  c.commit()
  return {'ok':True,'attempt_id':aid,'status':'started','resumed':False,'started':now,'limit':EXAM_LIMIT_SECONDS}
 except Exception:
  c.rollback()
  raise
 finally: c.close()

@app.post('/api/exam/answer')
def save_exam_answer(x:AnswerSave,req:Request):
 u=require(req);c=db();a=c.execute("SELECT * FROM attempts WHERE user_id=? AND status='started' ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone()
 if not a:c.close();raise HTTPException(403,'Нет активной аттестации')
 if a['started'] and int(time.time())-a['started'] >= EXAM_LIMIT_SECONDS:
  now=int(time.time());c.execute("UPDATE attempts SET status='expired',finished=? WHERE id=?",(now,a['id']));audit(c,u,'Аттестация истекла',f'Попытка №{a["id"]}');c.commit();c.close();raise HTTPException(410,'Время аттестации истекло')
 q=c.execute('SELECT question_id FROM attempt_questions WHERE attempt_id=? AND question_id=?',(a['id'],x.question_id)).fetchone()
 if not q:c.close();raise HTTPException(404,'Вопрос не найден в текущей аттестации')
 c.execute('UPDATE attempt_questions SET answer=? WHERE attempt_id=? AND question_id=?',(x.answer.strip(),a['id'],x.question_id));c.commit();c.close();return {'ok':True}

@app.get('/api/questions')
def questions(req:Request):
 u=require(req);c=db();a=c.execute("SELECT id FROM attempts WHERE user_id=? AND status='started' ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone()
 if not a:c.close();raise HTTPException(403,'Сначала начните аттестацию')
 rows=c.execute('SELECT aq.question_id,aq.body_snapshot,aq.answer,q.options,q.points FROM attempt_questions aq JOIN questions q ON q.id=aq.question_id WHERE aq.attempt_id=? ORDER BY aq.rowid',(a['id'],)).fetchall();c.close()
 return [{'id':r['question_id'],'body':r['body_snapshot'],'answer':r['answer'],'options':json.loads(r['options'] or '[]'),'points':r['points']} for r in rows]
@app.post('/api/submit')
def submit(x:Answers,req:Request):
 u=require(req);c=db();a=c.execute("SELECT * FROM attempts WHERE user_id=? AND status='started' ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone()
 if not a:c.close();raise HTTPException(403,'Нет активной аттестации')
 if a['started'] and int(time.time())-a['started'] >= EXAM_LIMIT_SECONDS:
  now=int(time.time());c.execute("UPDATE attempts SET status='expired',finished=? WHERE id=?",(now,a['id']));audit(c,u,'Аттестация истекла',f'Попытка №{a["id"]}');c.commit();c.close();raise HTTPException(410,'Время аттестации истекло. Ответы не приняты.')
 qs=c.execute('SELECT question_id FROM attempt_questions WHERE attempt_id=?',(a['id'],)).fetchall()
 if len(qs)!=33 or len(x.answers)!=33:c.close();raise HTTPException(400,'Необходимо ответить на все 33 вопроса')
 for q in qs:
  answer=str(x.answers.get(str(q['question_id']),'')).strip()
  if not answer:c.close();raise HTTPException(400,'Все ответы должны быть заполнены')
  c.execute('UPDATE attempt_questions SET answer=? WHERE attempt_id=? AND question_id=?',(answer,a['id'],q['question_id']))
 now=int(time.time());c.execute("UPDATE attempts SET answers=?,finished=?,status='pending_review' WHERE id=?",(json.dumps(x.answers,ensure_ascii=False),now,a['id']))
 audit(c,u,'Ответы отправлены на проверку',f'Попытка №{a["id"]} · 33 ответа');
 for inst in c.execute("SELECT id FROM users WHERE role IN ('Инструктор','Начальник ОСВ','Заместитель начальника ОСВ','Владелец') AND role_approved=1").fetchall():c.execute('INSERT INTO notifications(user_id,title,body,created) VALUES(?,?,?,?)',(inst['id'],'Новая аттестация',f'{u["nickname"]} отправил ответы на проверку',now))
 c.commit();c.close();return {'ok':True,'status':'pending_review','message':'Ответы отправлены инструктору на проверку'}
@app.get('/api/admin/reviews')
def reviews(req:Request):
 require(req,staff=True);c=db();rows=c.execute("SELECT a.id,a.user_id,a.created,a.started,a.finished,u.nickname,u.role FROM attempts a JOIN users u ON u.id=a.user_id WHERE a.status='pending_review' ORDER BY a.finished").fetchall();c.close();return [dict(r) for r in rows]
@app.get('/api/admin/reviews/{aid}')
def review_detail(aid:int,req:Request):
 require(req,staff=True);c=db();a=c.execute("SELECT a.*,u.nickname,u.role FROM attempts a JOIN users u ON u.id=a.user_id WHERE a.id=? AND a.status='pending_review'",(aid,)).fetchone()
 if not a:c.close();raise HTTPException(404,'Работа не найдена или уже проверена')
 rows=c.execute('SELECT question_id,body_snapshot,answer,mark,reviewed_by,reviewed_at FROM attempt_questions WHERE attempt_id=? ORDER BY rowid',(aid,)).fetchall();c.close();return {'attempt':dict(a),'answers':[dict(r) for r in rows]}
@app.post('/api/admin/reviews/{aid}/{qid}/{mark}')
def mark_answer(aid:int,qid:int,mark:int,req:Request):
 actor=require_staff_action(req)
 if mark not in (0,1):raise HTTPException(400,'Отметка должна быть 0 или 1')
 c=db();a=c.execute("SELECT * FROM attempts WHERE id=? AND status='pending_review'",(aid,)).fetchone();q=c.execute('SELECT * FROM attempt_questions WHERE attempt_id=? AND question_id=?',(aid,qid)).fetchone()
 if not a or not q:c.close();raise HTTPException(404,'Ответ не найден')
 c.execute('UPDATE attempt_questions SET mark=?,reviewed_by=?,reviewed_at=? WHERE attempt_id=? AND question_id=?',(mark,actor['nickname'],int(time.time()),aid,qid));audit(c,actor,'Ответ аттестации проверен',f'Попытка №{aid}, вопрос {qid}: {"верно" if mark else "неверно"}');c.commit();c.close();return {'ok':True}
@app.post('/api/admin/reviews/{aid}/finish')
def finish_review(aid:int,req:Request):
 actor=require_staff_action(req);c=db();a=c.execute("SELECT * FROM attempts WHERE id=? AND status='pending_review'",(aid,)).fetchone()
 if not a:c.close();raise HTTPException(404,'Работа не найдена')
 rows=c.execute('SELECT mark FROM attempt_questions WHERE attempt_id=?',(aid,)).fetchall()
 if len(rows)!=33 or any(r['mark'] is None for r in rows):c.close();raise HTTPException(400,'Проверьте все 33 ответа')
 score=sum(r['mark'] for r in rows);now=int(time.time());passed=score>=28;u=c.execute('SELECT * FROM users WHERE id=?',(a['user_id'],)).fetchone();c.execute("UPDATE attempts SET score=?,total=33,passed=?,status='finished',finished=? WHERE id=?",(score,int(passed),now,aid));
 if passed:
  c.execute('UPDATE users SET retake_required=0 WHERE id=?',(a['user_id'],))
 audit(c,actor,'Аттестация проверена',f'{u["nickname"]} · {score} ✓ / {33-score} ✕');
 if passed:
  c.execute('INSERT INTO notifications(user_id,title,body,created) VALUES(?,?,?,?)',(u['id'],'Аттестация проверена',f'Результат: {score} ✓ и {33-score} ✕ · Пройдена',now)); c.commit();c.close();return {'ok':True,'score':score,'wrong':33-score,'passed':True,'deleted':False}
 if u['role']=='Стажёр':
  audit(c,actor,'Сотрудник удалён после провала аттестации',f'{u["nickname"]} · {score}/33 · ниже проходного 28'); delete_user_data(c,u['id']); c.commit();c.close(); return {'ok':True,'score':score,'wrong':33-score,'passed':False,'deleted':True,'message':'Аттестация не пройдена. Аккаунт удалён из системы.'}
 c.execute('INSERT INTO notifications(user_id,title,body,created) VALUES(?,?,?,?)',(u['id'],'Аттестация не пройдена',f'Результат: {score}/33',now));c.commit();c.close();return {'ok':True,'score':score,'wrong':33-score,'passed':False,'deleted':False}
@app.post('/api/admin/users/{uid}/reattest')
def send_reattest(uid:int,req:Request):
 actor=require(req,owner=True)
 c=db();u=c.execute('SELECT * FROM users WHERE id=? AND nickname<>?',(uid,OWNER)).fetchone()
 if not u:c.close();raise HTTPException(404,'Пользователь не найден')
 c.execute('UPDATE users SET retake_required=1 WHERE id=?',(uid,));now=int(time.time());audit(c,actor,'Назначена переаттестация',f'{u["nickname"]} направлен на переаттестацию')
 c.execute('INSERT INTO notifications(user_id,title,body,created) VALUES(?,?,?,?)',(uid,'Переаттестация',f'Вас направили на переаттестацию. Доступна новая аттестация на 30 минут.',now));c.commit();c.close();return {'ok':True}

@app.get('/api/admin/questions')
def list_admin_questions(req:Request):
 require(req,staff=True); c=db(); rows=c.execute('SELECT id,body,options,correct,points,active FROM questions ORDER BY id DESC LIMIT 5000').fetchall(); c.close(); return [{'id':r['id'],'body':r['body'],'options':json.loads(r['options'] or '[]'),'correct':r['correct'],'points':r['points'],'active':bool(r['active'])} for r in rows]

@app.post('/api/admin/questions')
def add_question(x:QuestionIn,req:Request):
 require_staff_action(req);validate_question(x);c=db()
 if c.execute('SELECT COUNT(*) FROM questions').fetchone()[0]>=5000:c.close();raise HTTPException(400,'Достигнут лимит базы вопросов')
 cur=c.execute('INSERT INTO questions(body,options,correct,points,active) VALUES(?,?,?,1,?)',(x.body.strip(),json.dumps(x.options,ensure_ascii=False),x.correct,int(x.active)));c.commit();qid=cur.lastrowid;c.close();return {'id':qid}
@app.put('/api/admin/questions/{qid}')
def edit_question(qid:int,x:QuestionIn,req:Request):
 require_staff_action(req);validate_question(x);c=db();cur=c.execute('UPDATE questions SET body=?,options=?,correct=?,points=1,active=? WHERE id=?',(x.body.strip(),json.dumps(x.options,ensure_ascii=False),x.correct,int(x.active),qid));c.commit();c.close()
 if not cur.rowcount:raise HTTPException(404,'Вопрос не найден')
 return {'ok':True}
@app.delete('/api/admin/questions/{qid}')
def delete_question(qid:int,req:Request):
 require_staff_action(req);c=db();c.execute('DELETE FROM questions WHERE id=?',(qid,));c.commit();c.close();return {'ok':True}
@app.post('/api/admin/questions/bulk')
def bulk_questions(payload:dict,req:Request):
 actor=require_staff_action(req);raw=payload.get('text','');items=payload.get('questions',[])
 if raw:
  items += [{'body':line.strip()} for line in raw.splitlines() if line.strip()]
 cleaned=[]
 for item in items:
  body=(item.get('body') or item.get('question') or '').strip()
  body=re.sub(r'^\s*\d+\s*[\.)]\s*','',body).strip()
  if body and len(body)<=700:cleaned.append(body)
 if not cleaned:raise HTTPException(400,'Вставьте вопросы: по одному на строку, либо передайте массив questions')
 c=db();existing={r['body'].strip().casefold() for r in c.execute('SELECT body FROM questions').fetchall()};new=[q for q in cleaned if q.casefold() not in existing]
 if len(new)>1000 or len(existing)+len(new)>5000:c.close();raise HTTPException(400,'Лимит базы — 5000 вопросов')
 for body in new:c.execute('INSERT INTO questions(body,options,correct,points,active) VALUES(?,"[]",0,1,1)',(body,))
 audit(c,actor,'Массовая загрузка вопросов',f'Добавлено {len(new)} вопросов');c.commit();total=c.execute('SELECT COUNT(*) FROM questions WHERE active=1').fetchone()[0];c.close();return {'ok':True,'added':len(new),'duplicates':len(cleaned)-len(new),'active_total':total}
@app.get('/api/notifications')
def notifications(req:Request):
 u=require(req);c=db();rows=c.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY created DESC LIMIT 100',(u['id'],)).fetchall();c.close();return [dict(r) for r in rows]
@app.post('/api/notifications/seen')
def notifications_seen(req:Request):
 u=require(req);c=db();c.execute('UPDATE notifications SET seen=1 WHERE user_id=?',(u['id'],));c.commit();c.close();return {'ok':True}
@app.get('/api/admin/users')
def admin_users(req:Request):
 require(req,staff=True);c=db();rows=c.execute('''SELECT u.id,u.nickname,u.mask,u.position,u.role,u.role_approved,u.role_requested,u.created,u.last_login,u.rank,
 (SELECT COUNT(*) FROM attempts a WHERE a.user_id=u.id) attempts_count,
 (SELECT score FROM attempts a WHERE a.user_id=u.id ORDER BY a.id DESC LIMIT 1) last_score,
 (SELECT total FROM attempts a WHERE a.user_id=u.id ORDER BY a.id DESC LIMIT 1) last_total,
 (SELECT passed FROM attempts a WHERE a.user_id=u.id ORDER BY a.id DESC LIMIT 1) last_passed,
 (SELECT status FROM attempts a WHERE a.user_id=u.id ORDER BY a.id DESC LIMIT 1) last_attempt_status
 FROM users u ORDER BY created DESC''').fetchall();c.close();return [dict(r) for r in rows]
@app.get('/api/admin/role-requests')
def role_requests(req:Request):
 require(req,staff=True);c=db();rows=c.execute("SELECT id,nickname,position,COALESCE(NULLIF(role_requested,''),position) AS role_requested,role,role_approved,created FROM users WHERE role_approved=0 AND nickname<>? ORDER BY created",(OWNER,)).fetchall();c.close();return [dict(r) for r in rows]
@app.post('/api/admin/role-requests/{uid}/{decision}')
def decide_role(uid:int,decision:str,req:Request):
 actor=require(req,owner=True)
 if decision not in ('approve','reject'):raise HTTPException(400,'Некорректное решение')
 c=db();u=c.execute('SELECT * FROM users WHERE id=? AND nickname<>?',(uid,OWNER)).fetchone()
 if not u:c.close();raise HTTPException(404,'Пользователь не найден')
 old_role=u['role']; requested=u['role_requested'] or u['position'] or 'Стажёр'
 if decision=='approve':
  c.execute('UPDATE users SET role=?,position=?,role_approved=1 WHERE id=?',(requested,requested,uid));event='Должность одобрена';new_role=requested
  c.execute('INSERT INTO user_history(user_id,actor,field,old_value,new_value,created) VALUES(?,?,?,?,?,?)',(uid,actor['nickname'],'Должность',old_role,new_role,int(time.time())))
  c.execute('INSERT INTO notifications(user_id,title,body,created) VALUES(?,?,?,?)',(uid,'Заявка одобрена',f'Вам назначена должность: {new_role}',int(time.time())))
 else:
  c.execute("UPDATE users SET role_approved=0,role='Стажёр' WHERE id=?",(uid,));event='Должность отклонена';new_role='Стажёр'
  c.execute('INSERT INTO user_history(user_id,actor,field,old_value,new_value,created) VALUES(?,?,?,?,?,?)',(uid,actor['nickname'],'Заявка на должность',requested,new_role,int(time.time())))
  c.execute('INSERT INTO notifications(user_id,title,body,created) VALUES(?,?,?,?)',(uid,'Заявка отклонена',f'Заявка на должность {requested} отклонена',int(time.time())))
 audit(c,actor,event,f"{u['nickname']} · {requested}");c.commit();c.close();return {'ok':True}
@app.get('/api/admin/exam-requests')
def admin_exam_requests(req:Request):
 require(req,staff=True);c=db();rows=c.execute("SELECT r.id,r.user_id,r.status,r.created,r.reviewed,r.reviewed_by,u.nickname,u.role FROM exam_requests r JOIN users u ON u.id=r.user_id ORDER BY CASE r.status WHEN 'pending' THEN 0 ELSE 1 END,r.created DESC").fetchall();c.close();return [dict(r) for r in rows]
@app.post('/api/admin/exam-requests/{rid}/{decision}')
def decide_exam(rid:int,decision:str,req:Request):
 actor=require_staff_action(req)
 if decision not in ('approve','reject'):raise HTTPException(400,'Некорректное решение')
 c=db();r=c.execute('SELECT r.*,u.nickname,u.role_approved FROM exam_requests r JOIN users u ON u.id=r.user_id WHERE r.id=?',(rid,)).fetchone()
 if not r:c.close();raise HTTPException(404,'Заявка не найдена')
 if not r['role_approved']:c.close();raise HTTPException(400,'Сначала одобрите должность участника')
 status='approved' if decision=='approve' else 'rejected';now=int(time.time());c.execute('UPDATE exam_requests SET status=?,reviewed=?,reviewed_by=? WHERE id=?',(status,now,actor['nickname'],rid));audit(c,actor,'Заявка на аттестацию '+('одобрена' if decision=='approve' else 'отклонена'),f"{r['nickname']} · заявка №{rid}");c.commit();c.close();return {'ok':True,'status':status}
@app.patch('/api/admin/users/{uid}/role')
def set_role(uid:int,x:RoleIn,req:Request):
 actor=require(req,owner=True)
 if x.role not in ROLES:raise HTTPException(400,'Недопустимая должность')
 if actor['role']!='Владелец' and x.role=='Начальник ОСВ':
  c=db();existing=c.execute('SELECT role FROM users WHERE id=? AND nickname<>?',(uid,OWNER)).fetchone();c.close()
  if not existing or existing['role']!='Начальник ОСВ':raise HTTPException(403,'Назначать начальника ОСВ может только Fenix_Dinero')
 old_role=u['role']; c=db();cur=c.execute("UPDATE users SET role=?,role_requested=?,role_approved=1,rank=CASE WHEN ? IN ('Начальник ОСВ','Заместитель начальника ОСВ') THEN rank ELSE 'Без звания' END WHERE id=? AND nickname<>?",(x.role,x.role,x.role,uid,OWNER));u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
 if not cur.rowcount:c.close();raise HTTPException(404,'Пользователь не найден')
 c.execute('INSERT INTO user_history(user_id,actor,field,old_value,new_value,created) VALUES(?,?,?,?,?,?)',(uid,actor['nickname'],'Должность',old_role,x.role,int(time.time()))); audit(c,actor,'Должность изменена',f"{u['nickname']} · {x.role}"); c.execute('INSERT INTO notifications(user_id,title,body,created) VALUES(?,?,?,?)',(uid,'Изменена должность',f'Новая должность: {x.role}',int(time.time()))); c.commit();c.close();return {'ok':True}
@app.delete('/api/admin/exam-requests/{rid}')
def delete_exam_request(rid:int,req:Request):
 actor=require(req,owner=True);c=db();r=c.execute('SELECT r.*,u.nickname FROM exam_requests r JOIN users u ON u.id=r.user_id WHERE r.id=?',(rid,)).fetchone()
 if not r:c.close();raise HTTPException(404,'Заявка не найдена')
 audit(c,actor,'Заявка на аттестацию удалена',f"{r['nickname']} · заявка №{rid}");c.execute('DELETE FROM exam_requests WHERE id=?',(rid,));c.commit();c.close();return {'ok':True}
@app.patch('/api/admin/users/{uid}/mask')
def set_mask(uid:int,x:MaskIn,req:Request):
 actor=require(req,owner=True)
 if not x.mask.isdigit(): raise HTTPException(400,'Маска должна содержать только цифры')
 c=db();u=c.execute('SELECT * FROM users WHERE id=? AND nickname<>?',(uid,OWNER)).fetchone()
 if not u:c.close();raise HTTPException(404,'Пользователь не найден или защищённый аккаунт')
 c.execute('UPDATE users SET mask=? WHERE id=?',(x.mask.strip(),uid));c.execute('INSERT INTO user_history(user_id,actor,field,old_value,new_value,created) VALUES(?,?,?,?,?,?)',(uid,actor['nickname'],'Маска',u['mask'],x.mask.strip(),int(time.time())));audit(c,actor,'Маска изменена',f"{u['nickname']} · {x.mask.strip()}");c.commit();c.close();return {'ok':True,'mask':x.mask.strip()}
@app.patch('/api/admin/users/{uid}/rank')
def set_rank(uid:int,x:RoleIn,req:Request):
 actor=require(req,owner=True)
 if x.role not in RANKS:raise HTTPException(400,'Недопустимое звание')
 c=db();u=c.execute('SELECT * FROM users WHERE id=? AND nickname<>?',(uid,OWNER)).fetchone()
 if not u:c.close();raise HTTPException(404,'Пользователь не найден')
 if u['role'] not in ('Начальник ОСВ','Заместитель начальника ОСВ') and x.role!='Без звания':c.close();raise HTTPException(400,'Звание можно назначать только начальнику или заместителю ОСВ')
 c.execute('UPDATE users SET rank=? WHERE id=?',(x.role,uid));c.execute('INSERT INTO user_history(user_id,actor,field,old_value,new_value,created) VALUES(?,?,?,?,?,?)',(uid,actor['nickname'],'Звание',u['rank'],x.role,int(time.time())));audit(c,actor,'Звание изменено',f"{u['nickname']} · {x.role}");c.commit();c.close();return {'ok':True,'rank':x.role}
class AdminToggle(BaseModel):
 enabled: bool

@app.get('/api/admin/administrators')
def administrators(req:Request):
 require(req,owner=True); c=db(); rows=c.execute("SELECT id,nickname,mask,rank,last_login,created FROM users WHERE role='Администратор' AND role_approved=1 ORDER BY nickname COLLATE NOCASE").fetchall(); c.close(); return [dict(r) for r in rows]

@app.post('/api/admin/users/{uid}/admin')
def toggle_admin(uid:int,x:AdminToggle,req:Request):
 actor=require(req,owner=True)
 c=db(); u=c.execute('SELECT * FROM users WHERE id=? AND nickname<>?',(uid,OWNER)).fetchone()
 if not u: c.close(); raise HTTPException(404,'Пользователь не найден или защищённый аккаунт')
 old=u['role']; new='Администратор' if x.enabled else ('Стажёр' if not u['role_approved'] else (u['role_requested'] or u['position'] or 'Инспектор'))
 if x.enabled:
  c.execute("UPDATE users SET role='Администратор',role_requested='Администратор',role_approved=1 WHERE id=?",(uid,))
  event='Администратор назначен'
  body='Вам выданы права администратора. Доступ доступен только для контроля и просмотра.'
 else:
  if old!='Администратор': c.close(); raise HTTPException(400,'Пользователь не является администратором')
  if new=='Администратор': new='Инспектор'
  c.execute("UPDATE users SET role=?,role_requested=? WHERE id=?",(new,new,uid))
  event='Права администратора сняты'
  body=f'Права администратора сняты. Текущая должность: {new}'
 c.execute('INSERT INTO user_history(user_id,actor,field,old_value,new_value,created) VALUES(?,?,?,?,?,?)',(uid,actor['nickname'],'Администратор',old,new,int(time.time())))
 audit(c,actor,event,f"{u['nickname']} · {old} → {new}")
 c.execute('INSERT INTO notifications(user_id,title,body,created) VALUES(?,?,?,?)',(uid,event,body,int(time.time())))
 c.commit(); c.close(); return {'ok':True,'role':new}

@app.delete('/api/admin/users/{uid}')
def delete_user(uid:int,req:Request):
 actor=require(req,owner=True);c=db();u=c.execute('SELECT * FROM users WHERE id=? AND nickname<>?',(uid,OWNER)).fetchone()
 if not u:c.close();raise HTTPException(404,'Пользователь не найден или защищённый аккаунт')
 audit(c,actor,'Пользователь удалён',f"{u['nickname']} · {u['role']}")
 c.execute('DELETE FROM exam_requests WHERE user_id=?',(uid,));c.execute('DELETE FROM attempt_questions WHERE attempt_id IN (SELECT id FROM attempts WHERE user_id=?)',(uid,));c.execute('DELETE FROM notifications WHERE user_id=?',(uid,));c.execute('DELETE FROM personnel_notes WHERE user_id=?',(uid,));c.execute('DELETE FROM attempts WHERE user_id=?',(uid,));c.execute('DELETE FROM users WHERE id=?',(uid,));c.commit();c.close();return {'ok':True}


# Personnel dossier and internal service communications
def can_manage_people(u): return u['role'] in ('Владелец','Начальник ОСВ')
def can_chat_room(u,room):
 if room=='general': return bool(u['role_approved'])
 if room=='leadership': return u['role'] in ('Владелец','Начальник ОСВ','Заместитель начальника ОСВ') and bool(u['role_approved'])
 return False
@app.get('/api/personnel/{uid}')
def personnel_dossier(uid:int,req:Request):
 actor=require(req); c=db(); target=c.execute('''SELECT id,nickname,mask,position,role,rank,created,role_approved,last_login,role_requested FROM users WHERE id=?''',(uid,)).fetchone()
 if not target: c.close(); raise HTTPException(404,'Сотрудник не найден')
 if actor['id']!=uid and not (actor['role'] in ('Владелец','Начальник ОСВ','Заместитель начальника ОСВ','Инструктор') and actor['role_approved']): c.close(); raise HTTPException(403,'Нет доступа к личному делу')
 hist=c.execute('SELECT actor,field,old_value,new_value,created FROM user_history WHERE user_id=? ORDER BY created DESC LIMIT 200',(uid,)).fetchall()
 notes=c.execute('SELECT id,kind,body,actor,created FROM personnel_notes WHERE user_id=? ORDER BY created DESC LIMIT 200',(uid,)).fetchall()
 exams=c.execute('SELECT id,score,total,passed,status,created,started,finished FROM attempts WHERE user_id=? ORDER BY id DESC LIMIT 100',(uid,)).fetchall(); c.close()
 return {'user':dict(target),'history':[dict(x) for x in hist],'notes':[dict(x) for x in notes],'exams':[dict(x) for x in exams],'stats':{'attempts':len(exams),'passed':sum(1 for x in exams if x['passed']),'failed':sum(1 for x in exams if x['status']=='finished' and not x['passed'])}}
@app.post('/api/personnel/{uid}/notes')
def personnel_note(uid:int,payload:dict,req:Request):
 actor=require(req); kind=str(payload.get('kind','')).strip(); body=str(payload.get('body','')).strip()
 if not can_manage_people(actor): raise HTTPException(403,'Только владелец или начальник может вносить записи')
 if kind not in ('Поощрение','Выговор','Замечание') or not body or len(body)>1500: raise HTTPException(400,'Укажите тип и текст записи')
 c=db(); target=c.execute('SELECT id,nickname FROM users WHERE id=? AND nickname<>?',(uid,OWNER)).fetchone()
 if not target: c.close(); raise HTTPException(404,'Сотрудник не найден или защищён')
 now=int(time.time()); c.execute('INSERT INTO personnel_notes(user_id,kind,body,actor,created) VALUES(?,?,?,?,?)',(uid,kind,body,actor['nickname'],now)); audit(c,actor,'Запись в личное дело',f'{target["nickname"]} · {kind}: {body[:160]}'); c.execute('INSERT INTO notifications(user_id,title,body,created) VALUES(?,?,?,?)',(uid,'Обновлено личное дело',f'{kind}: {body}',now)); c.commit(); c.close(); return {'ok':True}
@app.get('/api/chat/people')
def chat_people(req:Request):
 u=require(req); c=db(); rows=c.execute('SELECT id,nickname,role FROM users WHERE role_approved=1 AND id<>? ORDER BY nickname COLLATE NOCASE',(u['id'],)).fetchall(); c.close(); return [dict(x) for x in rows]
@app.get('/api/chat/messages')
def chat_messages(req:Request,room:str='general',peer:int|None=None):
 u=require(req); c=db()
 if room in ('general','leadership'):
  if not can_chat_room(u,room): c.close(); raise HTTPException(403,'Нет доступа к этому чату')
  rows=c.execute('SELECT m.id,m.room,m.sender_id,m.recipient_id,m.body,m.created,u.nickname sender FROM chat_messages m JOIN users u ON u.id=m.sender_id WHERE m.room=? ORDER BY m.id DESC LIMIT 100',(room,)).fetchall()
 elif room=='direct':
  if not peer or peer==u['id']: c.close(); raise HTTPException(400,'Выберите собеседника')
  rows=c.execute('SELECT m.id,m.room,m.sender_id,m.recipient_id,m.body,m.created,u.nickname sender FROM chat_messages m JOIN users u ON u.id=m.sender_id WHERE m.room=? AND ((m.sender_id=? AND m.recipient_id=?) OR (m.sender_id=? AND m.recipient_id=?)) ORDER BY m.id DESC LIMIT 100',('direct',u['id'],peer,peer,u['id'])).fetchall()
 else: c.close(); raise HTTPException(400,'Неизвестный чат')
 c.close(); return [dict(x) for x in reversed(rows)]
@app.post('/api/chat/messages')
def chat_send(payload:dict,req:Request):
 u=require(req); room=str(payload.get('room','general')); body=str(payload.get('body','')).strip(); peer=payload.get('peer')
 if not body or len(body)>2000: raise HTTPException(400,'Сообщение должно содержать 1–2000 символов')
 if room in ('general','leadership'):
  if not can_chat_room(u,room): raise HTTPException(403,'Нет доступа к этому чату')
  recipient=None
 elif room=='direct':
  try: peer=int(peer)
  except: raise HTTPException(400,'Выберите собеседника')
  c=db(); other=c.execute('SELECT id FROM users WHERE id=? AND role_approved=1',(peer,)).fetchone(); c.close()
  if not other or peer==u['id']: raise HTTPException(404,'Собеседник недоступен')
  recipient=peer
 else: raise HTTPException(400,'Неизвестный чат')
 c=db(); now=int(time.time()); c.execute('INSERT INTO chat_messages(room,sender_id,recipient_id,body,created) VALUES(?,?,?,?,?)',(room,u['id'],recipient,body,now)); mid=c.execute('SELECT last_insert_rowid()').fetchone()[0]; audit(c,u,'Сообщение отправлено',f'{room} · #{mid}'); c.commit(); c.close(); return {'ok':True,'id':mid}
@app.get('/api/dashboard')
def dashboard(req:Request):
 u=require(req);c=db();now=int(time.time());
 staff=c.execute("SELECT COUNT(*) FROM users WHERE role_approved=1").fetchone()[0]
 requests=c.execute("SELECT COUNT(*) FROM users WHERE role_approved=0 AND nickname<>?",(OWNER,)).fetchone()[0]
 reviews=c.execute("SELECT COUNT(*) FROM attempts WHERE status='pending_review'").fetchone()[0]
 orders=c.execute("SELECT COUNT(*) FROM personnel_notes WHERE kind IN ('Выговор','Поощрение')").fetchone()[0]
 active=c.execute("SELECT COUNT(*) FROM users WHERE role_approved=1 AND last_login IS NOT NULL AND last_login>=?",(now-7*86400,)).fetchone()[0]
 events=c.execute('SELECT id,nickname,event,details,created FROM audit ORDER BY created DESC LIMIT 12').fetchall();c.close();return {'staff':staff,'requests':requests,'reviews':reviews,'orders':orders,'active_staff':active,'activity_percent':round((active/staff)*100) if staff else 0,'events':[dict(x) for x in events]}

@app.get('/api/admin/results')
def results(req:Request):
 require(req,staff=True);c=db();rows=c.execute('SELECT a.*,u.nickname,u.position,u.role FROM attempts a JOIN users u ON u.id=a.user_id ORDER BY COALESCE(a.started,a.created) DESC LIMIT 500').fetchall();c.close();return [{'id':r['id'],'nickname':r['nickname'],'position':r['position'],'role':r['role'],'score':r['score'],'total':r['total'],'passed':bool(r['passed']),'created':r['created'],'started':r['started'],'finished':r['finished'],'status':r['status']} for r in rows]
@app.get('/api/admin/audit')
def audit_log(req:Request):
 require(req,staff=True);c=db();rows=c.execute('SELECT * FROM audit ORDER BY created DESC LIMIT 1000').fetchall();c.close();return [dict(r) for r in rows]
