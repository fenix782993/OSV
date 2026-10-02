import os, sqlite3, hashlib, hmac, secrets, json, time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
ROOT=Path(__file__).resolve().parent; DB=ROOT/"osv.db"
app=FastAPI(title="ОСВ — Аттестация",version="2.0.0")
app.mount("/static",StaticFiles(directory=ROOT/"static"),name="static")
SECRET=os.getenv("APP_SECRET","change-this-secret-on-render").encode(); OWNER="Fenix_Dinero"; PASS_SCORE=28; QUESTION_COUNT=33
ROLES=["Начальник ОСВ","Заместитель начальника ОСВ","Стажёр","Старший инспектор","Инспектор","Инструктор"]
QUESTIONS=[
  [
    "Какова основная задача ОСВ?",
    [
      "Организация мероприятий",
      "Контроль соблюдения сотрудниками законности и дисциплины",
      "Выдача удостоверений",
      "Организация дорожного движения"
    ],
    1
  ],
  [
    "Что должен сделать сотрудник ОСВ при получении информации о нарушении сотрудником?",
    [
      "Проверить информацию",
      "Сразу наказать",
      "Опубликовать информацию",
      "Игнорировать"
    ],
    0
  ],
  [
    "Основной принцип служебной проверки?",
    [
      "Объективность",
      "Предвзятость",
      "Сокрытие информации",
      "Заранее назначенное наказание"
    ],
    0
  ],
  [
    "Как сотрудник ОСВ должен общаться с проверяемым сотрудником?",
    [
      "С угрозами",
      "Корректно и в рамках полномочий",
      "Провоцировать конфликт",
      "Игнорировать"
    ],
    1
  ],
  [
    "Для чего используется служебный рапорт?",
    [
      "Для развлечения",
      "Для личной переписки",
      "Для фиксации служебной информации",
      "Для публикации новостей"
    ],
    2
  ],
  [
    "Что делать при конфликте интересов?",
    [
      "Скрыть его",
      "Продолжить проверку в личных интересах",
      "Сообщить руководству и действовать по процедуре",
      "Удалить материалы"
    ],
    2
  ],
  [
    "Что необходимо сделать перед служебным действием, если это предусмотрено регламентом?",
    [
      "Представиться и сообщить основание действий",
      "Скрыть должность",
      "Сразу применить максимальные меры",
      "Отказаться от фиксации"
    ],
    0
  ],
  [
    "Что такое служебная субординация?",
    [
      "Личные просьбы руководителя",
      "Установленный порядок взаимодействия и подчинения",
      "Отказ от распоряжений",
      "Самостоятельное изменение структуры"
    ],
    1
  ],
  [
    "Можно ли использовать служебные полномочия для личной выгоды?",
    [
      "Да",
      "Да, при высоком звании",
      "Только если никто не заметит",
      "Нет"
    ],
    3
  ],
  [
    "Что делать при выявлении нарушения вне компетенции ОСВ?",
    [
      "Самостоятельно принять любое решение",
      "Скрыть нарушение",
      "Передать информацию компетентному подразделению",
      "Удалить сведения"
    ],
    2
  ],
  [
    "Что важно при оценке доказательств?",
    [
      "Популярность свидетеля",
      "Звание сотрудника",
      "Количество сообщений",
      "Достоверность, относимость и законность получения"
    ],
    3
  ],
  [
    "Что делать при обнаружении ошибки в служебном документе?",
    [
      "Исправить установленным способом",
      "Удалить документ",
      "Оставить ошибку",
      "Обвинить другого сотрудника"
    ],
    0
  ],
  [
    "Что является превышением служебных полномочий?",
    [
      "Выполнение обязанностей",
      "Составление рапорта",
      "Доклад руководителю",
      "Действия за пределами предоставленных полномочий"
    ],
    3
  ],
  [
    "Как обращаться с конфиденциальной служебной информацией?",
    [
      "Публиковать в соцсетях",
      "Передавать знакомым",
      "Передавать в общий чат",
      "Не разглашать лицам без соответствующего доступа"
    ],
    3
  ],
  [
    "Что делать при поступлении жалобы на сотрудника?",
    [
      "Удалить жалобу",
      "Рассмотреть или передать по установленной процедуре",
      "Сразу наказать сотрудника",
      "Игнорировать"
    ],
    1
  ],
  [
    "Что помогает избежать необоснованного обвинения?",
    [
      "Слухи",
      "Личная неприязнь",
      "Проверка фактов и материалов",
      "Внешний вид сотрудника"
    ],
    2
  ],
  [
    "Как поступить с законным распоряжением руководителя в рамках его компетенции?",
    [
      "Исполнить установленным порядком",
      "Игнорировать",
      "Изменить самостоятельно",
      "Передать постороннему"
    ],
    0
  ],
  [
    "Зачем фиксировать результаты служебной проверки?",
    [
      "Чтобы скрыть ошибки",
      "Чтобы заменить все доказательства",
      "Чтобы сохранить информацию о действиях и выводах",
      "Чтобы избежать жалоб"
    ],
    2
  ],
  [
    "Как действовать при конфликте с проверяемым сотрудником?",
    [
      "Оскорблять",
      "Использовать полномочия для мести",
      "Отказаться от фиксации",
      "Сохранять спокойствие и действовать в рамках полномочий"
    ],
    3
  ],
  [
    "Что является ключевым требованием к сотруднику ОСВ?",
    [
      "Личные связи",
      "Законность, объективность и дисциплина",
      "Возможность менять правила",
      "Игнорирование процедур"
    ],
    1
  ],
  [
    "Имеет ли сотрудник право использовать служебную информацию в личных целях?",
    [
      "Да",
      "Только после смены",
      "Только с разрешения коллеги",
      "Нет"
    ],
    3
  ],
  [
    "Что должен сделать сотрудник при получении информации о коррупционном нарушении?",
    [
      "Скрыть информацию",
      "Сообщить и действовать по установленной процедуре",
      "Обсудить с друзьями",
      "Удалить сообщение"
    ],
    1
  ],
  [
    "Что является основанием для проведения проверки?",
    [
      "Проверяемая информация о возможном нарушении",
      "Личная неприязнь",
      "Слухи без проверки",
      "Желание наказать сотрудника"
    ],
    0
  ],
  [
    "Может ли сотрудник ОСВ самостоятельно изменить установленный порядок проведения проверки?",
    [
      "Да, всегда",
      "Да, если ему удобнее",
      "Нет, только в рамках предусмотренной процедуры",
      "Да, если проверяемый согласен"
    ],
    2
  ],
  [
    "Что необходимо соблюдать при работе со служебными материалами?",
    [
      "Сохранность и установленный порядок доступа",
      "Свободное распространение",
      "Передачу друзьям",
      "Удаление после прочтения"
    ],
    0
  ],
  [
    "Что должен содержать служебный рапорт?",
    [
      "Только мнение автора",
      "Достоверные сведения об обстоятельствах события",
      "Личные оскорбления",
      "Непроверенные слухи"
    ],
    1
  ],
  [
    "Как должен поступить сотрудник при обнаружении нарушения со стороны своего знакомого?",
    [
      "Скрыть нарушение",
      "Помочь избежать проверки",
      "Действовать объективно и по процедуре",
      "Уничтожить материалы"
    ],
    2
  ],
  [
    "Допустимо ли давление на свидетеля при служебной проверке?",
    [
      "Да",
      "Да, если дело важное",
      "Только по просьбе руководителя",
      "Нет"
    ],
    3
  ],
  [
    "Что следует сделать при недостатке информации для принятия решения?",
    [
      "Придумать недостающие сведения",
      "Провести дополнительную проверку",
      "Сразу наказать сотрудника",
      "Закрыть дело без проверки"
    ],
    1
  ],
  [
    "Что означает объективность сотрудника ОСВ?",
    [
      "Отсутствие личной заинтересованности и учет фактов",
      "Поддержка своего знакомого",
      "Наказание независимо от обстоятельств",
      "Доверие только одной стороне"
    ],
    0
  ],
  [
    "Как следует хранить материалы служебной проверки?",
    [
      "В личном телефоне",
      "В общем публичном чате",
      "В установленном для служебных материалов порядке",
      "У знакомого сотрудника"
    ],
    2
  ],
  [
    "Что делать, если проверяемый сотрудник предоставляет дополнительные доказательства?",
    [
      "Игнорировать их",
      "Рассмотреть их в рамках проверки",
      "Сразу удалить",
      "Запретить их предоставление"
    ],
    1
  ],
  [
    "Какой принцип должен лежать в основе работы ОСВ?",
    [
      "Личная выгода",
      "Предвзятость",
      "Законность, объективность и ответственность",
      "Сокрытие нарушений"
    ],
    2
  ]
]
def db():
 c=sqlite3.connect(DB,timeout=20); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON")
 c.executescript("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,nickname TEXT UNIQUE NOT NULL,position TEXT NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'Стажёр',created INTEGER NOT NULL,role_approved INTEGER NOT NULL DEFAULT 0,last_login INTEGER,role_requested TEXT); CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY AUTOINCREMENT,body TEXT NOT NULL,options TEXT NOT NULL,correct INTEGER NOT NULL,points INTEGER NOT NULL DEFAULT 1,active INTEGER NOT NULL DEFAULT 1); CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,score INTEGER NOT NULL DEFAULT 0,total INTEGER NOT NULL DEFAULT 33,passed INTEGER NOT NULL DEFAULT 0,answers TEXT NOT NULL DEFAULT '{}',created INTEGER NOT NULL,started INTEGER,finished INTEGER,status TEXT NOT NULL DEFAULT 'started',FOREIGN KEY(user_id) REFERENCES users(id)); CREATE TABLE IF NOT EXISTS exam_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created INTEGER NOT NULL,reviewed INTEGER,reviewed_by TEXT,FOREIGN KEY(user_id) REFERENCES users(id)); CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,nickname TEXT NOT NULL,event TEXT NOT NULL,details TEXT NOT NULL DEFAULT '',created INTEGER NOT NULL);")
 # additive migrations for existing databases
 cols={r['name'] for r in c.execute('PRAGMA table_info(users)')}
 for name,ddl in [('role_approved','INTEGER NOT NULL DEFAULT 0'),('last_login','INTEGER'),('role_requested','TEXT')]:
  if name not in cols: c.execute(f'ALTER TABLE users ADD COLUMN {name} {ddl}')
 acols={r['name'] for r in c.execute('PRAGMA table_info(attempts)')}
 for name,ddl in [('started','INTEGER'),('finished','INTEGER'),('status',"TEXT NOT NULL DEFAULT 'started'")]:
  if name not in acols: c.execute(f'ALTER TABLE attempts ADD COLUMN {name} {ddl}')
 c.commit(); return c
def audit(c,u,event,details=''):
 c.execute('INSERT INTO audit(user_id,nickname,event,details,created) VALUES(?,?,?,?,?)',(u['id'] if u else None,u['nickname'] if u else 'system',event,details,int(time.time())))
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
 if staff and u['role'] not in ('Владелец','Инструктор'):raise HTTPException(403,'Недостаточно прав')
 if owner and u['role']!='Владелец':raise HTTPException(403,'Только владелец может одобрять заявки')
 return u
class Register(BaseModel): nickname:str=Field(min_length=3,max_length=32); position:str=Field(min_length=2,max_length=60); password:str=Field(min_length=6,max_length=100)
class Login(BaseModel): nickname:str; password:str
class QuestionIn(BaseModel): body:str=Field(min_length=3,max_length=700); options:list[str]; correct:int; points:int=Field(default=1,ge=1,le=1); active:bool=True
class Answers(BaseModel): answers:dict[str,int]
class RoleIn(BaseModel): role:str
@app.on_event('startup')
def startup():
 c=db(); n=c.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
 if n==0:
  for body,options,correct in QUESTIONS:c.execute('INSERT INTO questions(body,options,correct,points,active) VALUES(?,?,?,1,1)',(body,json.dumps(options,ensure_ascii=False),correct))
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
def health():return {'status':'online','service':'OSV Attestation'}
def user_dict(u):return {'id':u['id'],'nickname':u['nickname'],'position':u['position'],'role':u['role'],'role_approved':bool(u['role_approved']),'role_requested':u['role_requested'],'last_login':u['last_login']}
@app.post('/api/register')
def register(x:Register,response:Response):
 nick=x.nickname.strip(); role=x.position.strip()
 if role not in ROLES:raise HTTPException(400,'Выберите должность из списка')
 c=db()
 try:
  cur=c.execute("INSERT INTO users(nickname,position,password,role,created,role_approved,role_requested) VALUES(?,?,?,?,?,0,?)",(nick,role,pw_hash(x.password),'Стажёр',int(time.time()),role)); uid=cur.lastrowid
  u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone();audit(c,u,'Регистрация',f'Запрошена должность: {role}');c.commit()
 except sqlite3.IntegrityError:c.close();raise HTTPException(409,'Такой игровой ник уже зарегистрирован')
 c.close();response.set_cookie('osv_session',token(uid),httponly=True,samesite='lax',secure=os.getenv('COOKIE_SECURE','0')=='1',max_age=1209600);return {'ok':True}
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
def roster():
 c=db();rows=c.execute("SELECT id,nickname,role,role_approved,created FROM users WHERE role_approved=1 ORDER BY CASE role WHEN 'Владелец' THEN 0 WHEN 'Начальник ОСВ' THEN 1 WHEN 'Заместитель начальника ОСВ' THEN 2 WHEN 'Старший инспектор' THEN 3 WHEN 'Инспектор' THEN 4 WHEN 'Инструктор' THEN 5 ELSE 6 END,nickname COLLATE NOCASE").fetchall();c.close();return [dict(r) for r in rows]
@app.post('/api/exam/request')
def exam_request(req:Request):
 u=require(req)
 if not u['role_approved']:raise HTTPException(403,'Сначала дождитесь подтверждения должности владельцем')
 if u['role']=='Владелец':return {'ok':True,'status':'approved'}
 c=db();old=c.execute("SELECT * FROM exam_requests WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone()
 if old:c.close();return {'ok':True,'status':'pending'}
 cur=c.execute("INSERT INTO exam_requests(user_id,status,created) VALUES(?,'pending',?)",(u['id'],int(time.time())));audit(c,u,'Заявка на аттестацию подана',f'Заявка №{cur.lastrowid}');c.commit();c.close();return {'ok':True,'status':'pending'}
@app.get('/api/questions')
def questions(req:Request):
 u=require(req);c=db()
 if u['role']!='Владелец':
  approved=c.execute("SELECT 1 FROM exam_requests WHERE user_id=? AND status='approved' ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone()
  if not approved:c.close();raise HTTPException(403,'Доступ закрыт. Подайте заявку и дождитесь одобрения владельца.')
  active=c.execute("SELECT 1 FROM attempts WHERE user_id=? AND status='started' ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone()
  if not active:c.close();raise HTTPException(403,'Сначала нажмите «Начать аттестацию»')
 rows=c.execute('SELECT id,body,options,points FROM questions WHERE active=1 ORDER BY id').fetchall();c.close();return [{'id':r['id'],'body':r['body'],'options':json.loads(r['options']),'points':r['points']} for r in rows]
@app.post('/api/exam/start')
def exam_start(req:Request):
 u=require(req);c=db()
 if u['role']!='Владелец':
  a=c.execute("SELECT 1 FROM exam_requests WHERE user_id=? AND status='approved' ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone()
  if not a:c.close();raise HTTPException(403,'Аттестация закрыта до одобрения заявки владельцем')
  if c.execute("SELECT 1 FROM attempts WHERE user_id=? AND status='started'",(u['id'],)).fetchone():c.close();raise HTTPException(409,'Аттестация уже начата')
  if c.execute("SELECT COUNT(*) FROM questions WHERE active=1").fetchone()[0]!=QUESTION_COUNT:c.close();raise HTTPException(400,'Аттестация пока не готова: требуется 33 активных вопроса')
 now=int(time.time());cur=c.execute("INSERT INTO attempts(user_id,score,total,passed,answers,created,started,status) VALUES(?,0,33,0,'{}',?,?, 'started')",(u['id'],now,now));audit(c,u,'Аттестация начата',f'Попытка №{cur.lastrowid}');c.commit();c.close();return {'ok':True,'attempt_id':cur.lastrowid}
@app.get('/api/admin/questions')
def admin_questions(req:Request):
 require(req,staff=True);c=db();rows=c.execute('SELECT * FROM questions ORDER BY id').fetchall();c.close();return [{'id':r['id'],'body':r['body'],'options':json.loads(r['options']),'correct':r['correct'],'points':r['points'],'active':bool(r['active'])} for r in rows]
def validate_question(x):
 if len(x.options)<2 or len(x.options)>6 or any(not a.strip() for a in x.options) or x.correct<0 or x.correct>=len(x.options):raise HTTPException(400,'Добавьте 2–6 вариантов и укажите правильный')
@app.post('/api/admin/questions')
def add_question(x:QuestionIn,req:Request):
 require(req,staff=True);validate_question(x);c=db()
 if c.execute('SELECT COUNT(*) FROM questions').fetchone()[0]>=33:c.close();raise HTTPException(400,'Не более 33 вопросов')
 cur=c.execute('INSERT INTO questions(body,options,correct,points,active) VALUES(?,?,?,1,?)',(x.body.strip(),json.dumps(x.options,ensure_ascii=False),x.correct,int(x.active)));c.commit();qid=cur.lastrowid;c.close();return {'id':qid}
@app.put('/api/admin/questions/{qid}')
def edit_question(qid:int,x:QuestionIn,req:Request):
 require(req,staff=True);validate_question(x);c=db();cur=c.execute('UPDATE questions SET body=?,options=?,correct=?,points=1,active=? WHERE id=?',(x.body.strip(),json.dumps(x.options,ensure_ascii=False),x.correct,int(x.active),qid));c.commit();c.close()
 if not cur.rowcount:raise HTTPException(404,'Вопрос не найден')
 return {'ok':True}
@app.delete('/api/admin/questions/{qid}')
def delete_question(qid:int,req:Request):
 require(req,staff=True);c=db();c.execute('DELETE FROM questions WHERE id=?',(qid,));c.commit();c.close();return {'ok':True}
@app.get('/api/admin/users')
def admin_users(req:Request):
 require(req,staff=True);c=db();rows=c.execute('SELECT id,nickname,position,role,role_approved,role_requested,created,last_login FROM users ORDER BY created DESC').fetchall();c.close();return [dict(r) for r in rows]
@app.get('/api/admin/role-requests')
def role_requests(req:Request):
 require(req,owner=True);c=db();rows=c.execute("SELECT id,nickname,position,role_requested,created FROM users WHERE role_approved=0 AND nickname<>? ORDER BY created",(OWNER,)).fetchall();c.close();return [dict(r) for r in rows]
@app.post('/api/admin/role-requests/{uid}/{decision}')
def decide_role(uid:int,decision:str,req:Request):
 actor=require(req,owner=True)
 if decision not in ('approve','reject'):raise HTTPException(400,'Некорректное решение')
 c=db();u=c.execute('SELECT * FROM users WHERE id=? AND nickname<>?',(uid,OWNER)).fetchone()
 if not u:c.close();raise HTTPException(404,'Пользователь не найден')
 if decision=='approve':c.execute('UPDATE users SET role=COALESCE(role_requested,position),role_approved=1 WHERE id=?',(uid,));event='Должность одобрена'
 else:c.execute("UPDATE users SET role_approved=0,role='Стажёр' WHERE id=?",(uid,));event='Должность отклонена'
 audit(c,actor,event,f"{u['nickname']} · {u['role_requested']}");c.commit();c.close();return {'ok':True}
@app.get('/api/admin/exam-requests')
def admin_exam_requests(req:Request):
 require(req,owner=True);c=db();rows=c.execute("SELECT r.id,r.user_id,r.status,r.created,r.reviewed,r.reviewed_by,u.nickname,u.role FROM exam_requests r JOIN users u ON u.id=r.user_id ORDER BY CASE r.status WHEN 'pending' THEN 0 ELSE 1 END,r.created DESC").fetchall();c.close();return [dict(r) for r in rows]
@app.post('/api/admin/exam-requests/{rid}/{decision}')
def decide_exam(rid:int,decision:str,req:Request):
 actor=require(req,owner=True)
 if decision not in ('approve','reject'):raise HTTPException(400,'Некорректное решение')
 c=db();r=c.execute('SELECT r.*,u.nickname,u.role_approved FROM exam_requests r JOIN users u ON u.id=r.user_id WHERE r.id=?',(rid,)).fetchone()
 if not r:c.close();raise HTTPException(404,'Заявка не найдена')
 if not r['role_approved']:c.close();raise HTTPException(400,'Сначала одобрите должность участника')
 status='approved' if decision=='approve' else 'rejected';now=int(time.time());c.execute('UPDATE exam_requests SET status=?,reviewed=?,reviewed_by=? WHERE id=?',(status,now,actor['nickname'],rid));audit(c,actor,'Заявка на аттестацию '+('одобрена' if decision=='approve' else 'отклонена'),f"{r['nickname']} · заявка №{rid}");c.commit();c.close();return {'ok':True,'status':status}
@app.patch('/api/admin/users/{uid}/role')
def set_role(uid:int,x:RoleIn,req:Request):
 actor=require(req,owner=True)
 if x.role not in ROLES:raise HTTPException(400,'Недопустимая должность')
 c=db();cur=c.execute('UPDATE users SET role=?,role_requested=?,role_approved=1 WHERE id=? AND nickname<>?',(x.role,x.role,uid,OWNER));u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
 if not cur.rowcount:c.close();raise HTTPException(404,'Пользователь не найден')
 audit(c,actor,'Должность изменена',f"{u['nickname']} · {x.role}");c.commit();c.close();return {'ok':True}
@app.post('/api/submit')
def submit(x:Answers,req:Request):
 u=require(req);c=db()
 if u['role']!='Владелец' and not c.execute("SELECT 1 FROM exam_requests WHERE user_id=? AND status='approved' ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone():c.close();raise HTTPException(403,'Нет одобренного допуска к аттестации')
 attempt=c.execute("SELECT * FROM attempts WHERE user_id=? AND status='started' ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone()
 if not attempt and u['role']!='Владелец':c.close();raise HTTPException(403,'Сначала начните аттестацию')
 qs=c.execute('SELECT id,correct,points,options FROM questions WHERE active=1 ORDER BY id').fetchall()
 if len(qs)!=33 or len(x.answers)!=33:c.close();raise HTTPException(400,'Ответьте на все 33 вопроса; тест должен содержать 33 активных вопроса')
 score=0;detail={}
 for q in qs:
  qid=str(q['id']);val=x.answers.get(qid);opts=json.loads(q['options'])
  if val is None or val<0 or val>=len(opts):c.close();raise HTTPException(400,'Некорректный вариант ответа')
  ok=val==q['correct'];score+=int(ok);detail[qid]={'selected':val,'correct':q['correct'],'ok':ok}
 now=int(time.time());passed=score>=28
 if attempt:c.execute("UPDATE attempts SET score=?,total=33,passed=?,answers=?,finished=?,status='finished' WHERE id=?",(score,int(passed),json.dumps(detail),now,attempt['id']))
 else:c.execute("INSERT INTO attempts(user_id,score,total,passed,answers,created,started,finished,status) VALUES(?,?,?,?,?,?,?,?, 'finished')",(u['id'],score,33,int(passed),json.dumps(detail),now,now,now))
 audit(c,u,'Аттестация завершена',f'{score}/33 · '+('сдана' if passed else 'не сдана'));c.commit();c.close();return {'score':score,'total':33,'passed':passed,'required':28,'contact':'karl_limansky2025'}
@app.get('/api/admin/results')
def results(req:Request):
 require(req,staff=True);c=db();rows=c.execute('SELECT a.*,u.nickname,u.position,u.role FROM attempts a JOIN users u ON u.id=a.user_id ORDER BY COALESCE(a.started,a.created) DESC LIMIT 500').fetchall();c.close();return [{'id':r['id'],'nickname':r['nickname'],'position':r['position'],'role':r['role'],'score':r['score'],'total':r['total'],'passed':bool(r['passed']),'created':r['created'],'started':r['started'],'finished':r['finished'],'status':r['status']} for r in rows]
@app.get('/api/admin/audit')
def audit_log(req:Request):
 require(req,owner=True);c=db();rows=c.execute('SELECT * FROM audit ORDER BY created DESC LIMIT 1000').fetchall();c.close();return [dict(r) for r in rows]
