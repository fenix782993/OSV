OSV BLUE COMMAND V15 — FAST NEON COMMAND CENTER

Это полная версия портала ОСВ. Интерфейс сохраняет утверждённый синий COMMAND CENTER: левая панель, верхняя панель, карточки, таблицы, профиль, уведомления и отдельная мобильная компоновка.

DATABASE / NEON
Основная БД теперь PostgreSQL/Neon. Код автоматически использует DATABASE_URL, если переменная задана. SQLite остаётся локальным fallback для разработки. При заданном DATABASE_URL приложение использует Neon; автоматический перенос существующей SQLite-базы в Neon не выполняется — старые данные нужно импортировать отдельно.

Render Environment:
APP_SECRET — Generate Value
OWNER_PASSWORD — пароль владельца Fenix_Dinero
DATABASE_URL — строка подключения Neon PostgreSQL (вставить в Secret Environment Variable)
COOKIE_SECURE=1
DB_PATH=/var/data/osv.db — только fallback, если DATABASE_URL не задан

Не записывайте пароль Neon в GitHub, render.yaml или README. В Render вставьте строку подключения в DATABASE_URL как Secret.

REGISTRATION / ACCESS
- Неавторизованный пользователь сразу видит окно входа/регистрации.
- Уже авторизованный пользователь не может случайно открыть регистрацию: backend отклоняет попытку регистрации из существующей сессии.
- Новый аккаунт создаётся отдельной записью и после регистрации выполняется вход только в него.
- Ник уникален.
- Новые сотрудники получают роль Стажёр до одобрения заявленной должности.
- Обычная аттестация доступна только Стажёру; остальные получают доступ только после назначения переаттестации.

ATTESTATION
- 33 письменных вопроса.
- Случайный порядок.
- 3 минуты на каждый вопрос (серверный таймер); при истечении времени вопрос пропускается.
- Проходной 28/33.
- Инструктор/руководство проверяют все 33 ответа.
- Провал Стажёра ниже 28/33 после проверки удаляет аккаунт по действующему ТЗ.

V14 FEATURES
- Оперативная обстановка.
- Организационная структура с переходом в личное дело.
- Тренировочный режим без влияния на официальный результат.
- Массовые уведомления: всем / инструкторам / инспекторам / стажёрам / руководству / составу.
- Календарь мероприятий.
- Безопасность и блокировки.
- Архив сотрудников и восстановление.
- Экспорт состава в CSV/Excel-совместимый формат.
- Резервная JSON-копия данных для владельца.
- Публичная сводка /api/public/summary.
- История кадровых изменений.
- Администраторы: только Владелец выдаёт и снимает доступ. Администратор имеет режим просмотра и контроля без удаления и критических изменений.
- Fenix_Dinero защищён от удаления и критических изменений.

WINDOWS CMD
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

DEPLOYMENT (DEPLEXO / ASGI HOSTING)
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT

NEON
Используйте именно pooled connection string из Neon, если она у вас предоставлена. Значение DATABASE_URL хранится только в Render Environment/Secret и не попадает в архив.

PERFORMANCE FIXES V15
- PostgreSQL/Neon schema is initialized once at startup instead of running CREATE TABLE/ALTER TABLE on every request. Removed a call to a missing SQLite-to-PostgreSQL migration function that previously crashed startup.
- psycopg connection pool: 1–6 connections, so login, /api/me, dashboard and navigation reuse warm database connections.
- Dashboard no longer downloads the full personnel list just to show an 8-person preview.
- Dashboard and notifications load in parallel.
- PostgreSQL row-count queries use named aliases and no longer crash with dict_row.
- Added /favicon.ico, so Render logs no longer show repeated favicon 404s.


V18 — ПЕРЕАТТЕСТАЦИЯ / ЧЁРНЫЙ СПИСОК / ТАЙМЕР
- Индивидуальная переаттестация и кнопка переаттестации всему действующему составу доступны владельцу, начальнику, заместителю и инструктору.
- Чёрный список хранит любой ник и причину, даже если этот ник не зарегистрирован на сайте. Видят владелец, начальник, заместитель и администраторы; изменять записи могут владелец, начальник и заместитель.
- У каждого экзаменационного вопроса собственный серверный лимит 180 секунд. Во время аттестации интерфейс блокирует переходы в другие разделы; срок не приостанавливается при обновлении страницы или переключении вкладки браузера.
- Боковое меню прокручивается независимо от нижнего блока аккаунта.

DEPLEXO + NEON POSTGRESQL
1. В Deplexo открой настройки приложения и раздел Environment Variables.
2. Добавь DATABASE_URL со всей pooled connection string из Neon (включая sslmode=require). Можно вместо этого назвать переменную NEON_DATABASE_URL. Не используй вместо строки подключения только API-токен Neon.
3. Установи APP_SECRET как длинную случайную секретную строку. OWNER_PASSWORD — пароль владельца Fenix_Dinero для первоначального создания аккаунта; не публикуй значения секретов и не помещай их в GitHub. COOKIE_SECURE=1, если сайт доступен только по HTTPS.
4. Build command: pip install -r requirements.txt
5. Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
6. После запуска проверь /api/health. Он должен вернуть database=postgresql. Не удаляй старую базу, пока не проверишь вход, состав и вопросы на новой версии.
