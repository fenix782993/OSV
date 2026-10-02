
import os
import sqlite3
import hashlib
import hmac
import secrets
import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent
DB = ROOT / "osv.db"

app = FastAPI(title="ОСВ — Аттестация", version="1.0.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

SECRET = os.getenv("APP_SECRET", "change-this-secret-on-render").encode()
OWNER = "Fenix_Dinero"
PASS_SCORE = 28
QUESTION_COUNT = 33

# Правильный ответ указан индексом с нуля
# Все вопросы оцениваются в 1 балл
QUESTIONS = [
    (
        "Какова основная задача ОСВ?",
        ["Организация мероприятий",
         "Контроль соблюдения сотрудниками законности и дисциплины",
         "Выдача удостоверений",
         "Организация дорожного движения"], 1
    ),
    (
        "Что должен сделать сотрудник ОСВ при получении информации о нарушении сотрудником?",
        ["Проверить информацию",
         "Сразу наказать",
         "Опубликовать информацию",
         "Игнорировать"], 0
    ),
    (
        "Основной принцип служебной проверки?",
        ["Объективность",
         "Предвзятость",
         "Сокрытие информации",
         "Заранее назначенное наказание"], 0
    ),
    (
        "Как сотрудник ОСВ должен общаться с проверяемым сотрудником?",
        ["С угрозами",
         "Корректно и в рамках полномочий",
         "Провоцировать конфликт",
         "Игнорировать"], 1
    ),
    (
        "Для чего используется служебный рапорт?",
        ["Для развлечения",
         "Для личной переписки",
         "Для фиксации служебной информации",
         "Для публикации новостей"], 2
    ),
    (
        "Что делать при конфликте интересов?",
        ["Скрыть его",
         "Продолжить проверку в личных интересах",
         "Сообщить руководству и действовать по процедуре",
         "Удалить материалы"], 2
    ),
    (
        "Что необходимо сделать перед служебным действием, если это предусмотрено регламентом?",
        ["Представиться и сообщить основание действий",
         "Скрыть должность",
         "Сразу применить максимальные меры",
         "Отказаться от фиксации"], 0
    ),
    (
        "Что такое служебная субординация?",
        ["Личные просьбы руководителя",
         "Установленный порядок взаимодействия и подчинения",
         "Отказ от распоряжений",
         "Самостоятельное изменение структуры"], 1
    ),
    (
        "Можно ли использовать служебные полномочия для личной выгоды?",
        ["Да",
         "Да, при высоком звании",
         "Только если никто не заметит",
         "Нет"], 3
    ),
    (
        "Что делать при выявлении нарушения вне компетенции ОСВ?",
        ["Самостоятельно принять любое решение",
         "Скрыть нарушение",
         "Передать информацию компетентному подразделению",
         "Удалить сведения"], 2
    ),
    (
        "Что важно при оценке доказательств?",
        ["Популярность свидетеля",
         "Звание сотрудника",
         "Количество сообщений",
         "Достоверность, относимость и законность получения"], 3
    ),
    (
        "Что делать при обнаружении ошибки в служебном документе?",
        ["Исправить установленным способом",
         "Удалить документ",
         "Оставить ошибку",
         "Обвинить другого сотрудника"], 0
    ),
    (
        "Что является превышением служебных полномочий?",
        ["Выполнение обязанностей",
         "Составление рапорта",
         "Доклад руководителю",
         "Действия за пределами предоставленных полномочий"], 3
    ),
    (
        "Как обращаться с конфиденциальной служебной информацией?",
        ["Публиковать в соцсетях",
         "Передавать знакомым",
         "Передавать в общий чат",
         "Не разглашать лицам без соответствующего доступа"], 3
    ),
    (
        "Что делать при поступлении жалобы на сотрудника?",
        ["Удалить жалобу",
         "Рассмотреть или передать по установленной процедуре",
         "Сразу наказать сотрудника",
         "Игнорировать"], 1
    ),
    (
        "Что помогает избежать необоснованного обвинения?",
        ["Слухи",
         "Личная неприязнь",
         "Проверка фактов и материалов",
         "Внешний вид сотрудника"], 2
    ),
    (
        "Как поступить с законным распоряжением руководителя в рамках его компетенции?",
        ["Исполнить установленным порядком",
         "Игнорировать",
         "Изменить самостоятельно",
         "Передать постороннему"], 0
    ),
    (
        "Зачем фиксировать результаты служебной проверки?",
        ["Чтобы скрыть ошибки",
         "Чтобы заменить все доказательства",
         "Чтобы сохранить информацию о действиях и выводах",
         "Чтобы избежать жалоб"], 2
    ),
    (
        "Как действовать при конфликте с проверяемым сотрудником?",
        ["Оскорблять",
         "Использовать полномочия для мести",
         "Отказаться от фиксации",
         "Сохранять спокойствие и действовать в рамках полномочий"], 3
    ),
    (
        "Что является ключевым требованием к сотруднику ОСВ?",
        ["Личные связи",
         "Законность, объективность и дисциплина",
         "Возможность менять правила",
         "Игнорирование процедур"], 1
    ),
    (
        "Имеет ли сотрудник право использовать служебную информацию в личных целях?",
        ["Да",
         "Только после смены",
         "Только с разрешения коллеги",
         "Нет"], 3
    ),
    (
        "Что должен сделать сотрудник при получении информации о коррупционном нарушении?",
        ["Скрыть информацию",
         "Сообщить и действовать по установленной процедуре",
         "Обсудить с друзьями",
         "Удалить сообщение"], 1
    ),
    (
        "Что является основанием для проведения проверки?",
        ["Проверяемая информация о возможном нарушении",
         "Личная неприязнь",
         "Слухи без проверки",
         "Желание наказать сотрудника"], 0
    ),
    (
        "Может ли сотрудник ОСВ самостоятельно изменить установленный порядок проведения проверки?",
        ["Да, всегда",
         "Да, если ему удобнее",
         "Нет, только в рамках предусмотренной процедуры",
         "Да, если проверяемый согласен"], 2
    ),
    (
        "Что необходимо соблюдать при работе со служебными материалами?",
        ["Сохранность и установленный порядок доступа",
         "Свободное распространение",
         "Передачу друзьям",
         "Удаление после прочтения"], 0
    ),
    (
        "Что должен содержать служебный рапорт?",
        ["Только мнение автора",
         "Достоверные сведения об обстоятельствах события",
         "Личные оскорбления",
         "Непроверенные слухи"], 1
    ),
    (
        "Как должен поступить сотрудник при обнаружении нарушения со стороны своего знакомого?",
        ["Скрыть нарушение",
         "Помочь избежать проверки",
         "Действовать объективно и по процедуре",
         "Уничтожить материалы"], 2
    ),
    (
        "Допустимо ли давление на свидетеля при служебной проверке?",
        ["Да",
         "Да, если дело важное",
         "Только по просьбе руководителя",
         "Нет"], 3
    ),
    (
        "Что следует сделать при недостатке информации для принятия решения?",
        ["Придумать недостающие сведения",
         "Провести дополнительную проверку",
         "Сразу наказать сотрудника",
         "Закрыть дело без проверки"], 1
    ),
    (
        "Что означает объективность сотрудника ОСВ?",
        ["Отсутствие личной заинтересованности и учет фактов",
         "Поддержка своего знакомого",
         "Наказание независимо от обстоятельств",
         "Доверие только одной стороне"], 0
    ),
    (
        "Как следует хранить материалы служебной проверки?",
        ["В личном телефоне",
         "В общем публичном чате",
         "В установленном для служебных материалов порядке",
         "У знакомого сотрудника"], 2
    ),
    (
        "Что делать, если проверяемый сотрудник предоставляет дополнительные доказательства?",
        ["Игнорировать их",
         "Рассмотреть их в рамках проверки",
         "Сразу удалить",
         "Запретить их предоставление"], 1
    ),
    (
        "Какой принцип должен лежать в основе работы ОСВ?",
        ["Личная выгода",
         "Предвзятость",
         "Законность, объективность и ответственность",
         "Сокрытие нарушений"], 2
    ),
]


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT UNIQUE NOT NULL,
            position TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Кандидат',
            created INTEGER NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS questions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            body TEXT NOT NULL,
            options TEXT NOT NULL,
            correct INTEGER NOT NULL,
            points INTEGER NOT NULL DEFAULT 1,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS attempts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            passed INTEGER NOT NULL,
            answers TEXT NOT NULL,
            created INTEGER NOT NULL
        )
    """)
    c.commit()
    return c


def seed_questions(c):
    count = c.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    if count == 0:
        for body, options, correct in QUESTIONS:
            c.execute(
                """INSERT INTO questions
                   (body, options, correct, points, active)
                   VALUES (?, ?, ?, 1, 1)""",
                (body, json.dumps(options, ensure_ascii=False), correct)
            )
        c.commit()


def pw_hash(p, s=None):
    s = s or secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac(
        "sha256", p.encode(), s.encode(), 180000
    ).hex()
    return s + "$" + value


def check_pw(p, stored):
    try:
        s, v = stored.split("$", 1)
        actual = hashlib.pbkdf2_hmac(
            "sha256", p.encode(), s.encode(), 180000
        ).hex()
        return hmac.compare_digest(actual, v)
    except Exception:
        return False


def token(uid):
    raw = f"{uid}:{int(time.time()) + 86400 * 14}"
    sig = hmac.new(SECRET, raw.encode(), hashlib.sha256).hexdigest()
    return raw + "." + sig


def current(req):
    t = req.cookies.get("osv_session", "")
    try:
        raw, sig = t.rsplit(".", 1)
        expected = hmac.new(
            SECRET, raw.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None

        uid, exp = raw.split(":")
        if int(exp) < time.time():
            return None

        c = db()
        u = c.execute(
            "SELECT * FROM users WHERE id=?", (int(uid),)
        ).fetchone()
        c.close()
        return u
    except Exception:
        return None


def require(req, staff=False):
    u = current(req)
    if not u:
        raise HTTPException(401, "Войдите в аккаунт")
    if staff and u["role"] not in ("Владелец", "Инструктор"):
        raise HTTPException(403, "Недостаточно прав")
    return u


class Register(BaseModel):
    nickname: str = Field(min_length=3, max_length=32)
    position: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=6, max_length=100)


class Login(BaseModel):
    nickname: str
    password: str


class QuestionIn(BaseModel):
    body: str = Field(min_length=3, max_length=700)
    options: list[str]
    correct: int
    points: int = Field(default=1, ge=1, le=1)
    active: bool = True


class Answers(BaseModel):
    answers: dict[str, int]


class RoleIn(BaseModel):
    role: str


@app.on_event("startup")
def startup():
    c = db()
    seed_questions(c)

    owner = c.execute(
        "SELECT id FROM users WHERE nickname=?", (OWNER,)
    ).fetchone()

    if not owner:
        c.execute(
            """INSERT INTO users
               (nickname, position, password, role, created)
               VALUES (?, ?, ?, ?, ?)""",
            (
                OWNER,
                "Инструктор ОСВ",
                pw_hash(os.getenv("OWNER_PASSWORD", "ChangeMe_123!")),
                "Владелец",
                int(time.time())
            )
        )

    c.commit()
    c.close()


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "online", "service": "OSV Attestation"}


@app.post("/api/register")
def register(x: Register, response: Response):
    nickname = x.nickname.strip()
    position = x.position.strip()
    if not nickname or not position:
        raise HTTPException(400, "Заполните все поля")

    c = db()
    try:
        cur = c.execute(
            """INSERT INTO users
               (nickname, position, password, role, created)
               VALUES (?, ?, ?, ?, ?)""",
            (
                nickname, position, pw_hash(x.password),
                "Кандидат", int(time.time())
            )
        )
        c.commit()
        uid = cur.lastrowid
    except sqlite3.IntegrityError:
        c.close()
        raise HTTPException(409, "Такой игровой ник уже зарегистрирован")
    c.close()

    response.set_cookie(
        "osv_session", token(uid),
        httponly=True,
        samesite="lax",
        secure=os.getenv("COOKIE_SECURE", "0") == "1",
        max_age=1209600
    )
    return {"ok": True}


@app.post("/api/login")
def login(x: Login, response: Response):
    c = db()
    u = c.execute(
        "SELECT * FROM users WHERE nickname=?",
        (x.nickname.strip(),)
    ).fetchone()
    c.close()

    if not u or not check_pw(x.password, u["password"]):
        raise HTTPException(401, "Неверный ник или пароль")

    response.set_cookie(
        "osv_session", token(u["id"]),
        httponly=True,
        samesite="lax",
        secure=os.getenv("COOKIE_SECURE", "0") == "1",
        max_age=1209600
    )
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie("osv_session")
    return {"ok": True}


@app.get("/api/me")
def me(req: Request):
    u = current(req)
    if not u:
        return {"user": None}

    return {
        "user": {
            "id": u["id"],
            "nickname": u["nickname"],
            "position": u["position"],
            "role": u["role"]
        }
    }


@app.get("/api/roster")
def roster():
    c = db()
    rows = c.execute("""
        SELECT id, nickname, position, role, created
        FROM users
        ORDER BY
            CASE role
                WHEN 'Владелец' THEN 0
                WHEN 'Начальник ОСВ' THEN 1
                WHEN 'Заместитель начальника ОСВ' THEN 2
                WHEN 'Старший инспектор' THEN 3
                WHEN 'Инспектор' THEN 4
                WHEN 'Инструктор' THEN 5
                WHEN 'Стажёр' THEN 6
                ELSE 7
            END,
            nickname COLLATE NOCASE
    """).fetchall()
    c.close()
    return [dict(r) for r in rows]


@app.get("/api/questions")
def questions(req: Request):
    u = current(req)
    c = db()
    rows = c.execute("""
        SELECT id, body, options, points
        FROM questions
        WHERE active=1
        ORDER BY id
    """).fetchall()
    c.close()

    return [
        {
            "id": r["id"],
            "body": r["body"],
            "options": json.loads(r["options"]),
            "points": r["points"]
        }
        for r in rows
    ]


@app.get("/api/admin/questions")
def admin_questions(req: Request):
    require(req, True)
    c = db()
    rows = c.execute(
        "SELECT * FROM questions ORDER BY id"
    ).fetchall()
    c.close()

    return [
        {
            "id": r["id"],
            "body": r["body"],
            "options": json.loads(r["options"]),
            "correct": r["correct"],
            "points": r["points"],
            "active": bool(r["active"])
        }
        for r in rows
    ]


def validate_question(x):
    if (
        len(x.options) < 2
        or len(x.options) > 6
        or any(not a.strip() for a in x.options)
        or x.correct < 0
        or x.correct >= len(x.options)
    ):
        raise HTTPException(
            400, "Добавьте 2–6 вариантов и укажите правильный"
        )


@app.post("/api/admin/questions")
def add_question(x: QuestionIn, req: Request):
    require(req, True)
    validate_question(x)

    c = db()
    count = c.execute(
        "SELECT COUNT(*) FROM questions"
    ).fetchone()[0]

    if count >= QUESTION_COUNT:
        c.close()
        raise HTTPException(
            400, "В аттестации может быть не более 33 вопросов"
        )

    cur = c.execute(
        """INSERT INTO questions
           (body, options, correct, points, active)
           VALUES (?, ?, ?, 1, ?)""",
        (
            x.body.strip(),
            json.dumps(x.options, ensure_ascii=False),
            x.correct,
            int(x.active)
        )
    )
    c.commit()
    qid = cur.lastrowid
    c.close()
    return {"id": qid}


@app.put("/api/admin/questions/{qid}")
def edit_question(qid: int, x: QuestionIn, req: Request):
    require(req, True)
    validate_question(x)

    c = db()
    cur = c.execute(
        """UPDATE questions
           SET body=?, options=?, correct=?, points=1, active=?
           WHERE id=?""",
        (
            x.body.strip(),
            json.dumps(x.options, ensure_ascii=False),
            x.correct,
            int(x.active),
            qid
        )
    )
    c.commit()
    c.close()

    if not cur.rowcount:
        raise HTTPException(404, "Вопрос не найден")
    return {"ok": True}


@app.delete("/api/admin/questions/{qid}")
def delete_question(qid: int, req: Request):
    require(req, True)
    c = db()
    c.execute("DELETE FROM questions WHERE id=?", (qid,))
    c.commit()
    c.close()
    return {"ok": True}


@app.get("/api/admin/users")
def admin_users(req: Request):
    require(req, True)
    c = db()
    rows = c.execute("""
        SELECT id, nickname, position, role, created
        FROM users
        ORDER BY nickname
    """).fetchall()
    c.close()
    return [dict(r) for r in rows]


@app.patch("/api/admin/users/{uid}/role")
def set_role(uid: int, x: RoleIn, req: Request):
    actor = require(req, True)
    allowed = [
        "Кандидат",
        "Начальник ОСВ",
        "Заместитель начальника ОСВ",
        "Стажёр",
        "Инструктор",
        "Инспектор",
        "Старший инспектор"
    ]

    if x.role not in allowed:
        raise HTTPException(400, "Недопустимая должность")

    if actor["role"] != "Владелец":
        raise HTTPException(
            403, "Назначать должности может только владелец"
        )

    c = db()
    cur = c.execute(
        "UPDATE users SET role=? WHERE id=? AND nickname<>?",
        (x.role, uid, OWNER)
    )
    c.commit()
    c.close()

    if not cur.rowcount:
        raise HTTPException(404, "Пользователь не найден")

    return {"ok": True}


@app.post("/api/submit")
def submit(x: Answers, req: Request):
    u = require(req)
    c = db()

    qs = c.execute("""
        SELECT id, correct, points
        FROM questions
        WHERE active=1
        ORDER BY id
    """).fetchall()

    if len(qs) != QUESTION_COUNT:
        c.close()
        raise HTTPException(
            400,
            f"Аттестация пока не готова: активных вопросов "
            f"{len(qs)} из {QUESTION_COUNT}"
        )

    if len(x.answers) != QUESTION_COUNT:
        c.close()
        raise HTTPException(400, "Ответьте на все 33 вопроса")

    score = 0
    detail = {}

    for q in qs:
        qid = str(q["id"])
        val = x.answers.get(qid)

        if val is None or val < 0:
            c.close()
            raise HTTPException(400, "Ответьте на все вопросы")

        options_row = c.execute(
            "SELECT options FROM questions WHERE id=?",
            (q["id"],)
        ).fetchone()
        options = json.loads(options_row["options"])

        if val >= len(options):
            c.close()
            raise HTTPException(400, "Некорректный вариант ответа")

        ok = val == q["correct"]
        if ok:
            score += 1

        detail[qid] = {
            "selected": val,
            "correct": q["correct"],
            "ok": ok
        }

    total = QUESTION_COUNT
    passed = score >= PASS_SCORE

    c.execute(
        """INSERT INTO attempts
           (user_id, score, total, passed, answers, created)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            u["id"], score, total, int(passed),
            json.dumps(detail), int(time.time())
        )
    )
    c.commit()
    c.close()

    return {
        "score": score,
        "total": total,
        "passed": passed,
        "required": PASS_SCORE,
        "contact": "karl_limansky2025"
    }


@app.get("/api/admin/results")
def results(req: Request):
    require(req, True)
    c = db()
    rows = c.execute("""
        SELECT a.*, u.nickname, u.position
        FROM attempts a
        JOIN users u ON u.id=a.user_id
        ORDER BY a.created DESC
        LIMIT 200
    """).fetchall()
    c.close()

    return [
        {
            "nickname": r["nickname"],
            "position": r["position"],
            "score": r["score"],
            "total": r["total"],
            "passed": bool(r["passed"]),
            "created": r["created"]
        }
        for r in rows
    ]
