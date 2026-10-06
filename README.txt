ОСВ — RED COMMAND PORTAL

Что внутри:
- FastAPI backend с существующей логикой авторизации, заявок, аттестации, ролей, вопросов, результатов, аудита и чата.
- Новый красно-чёрный интерфейс с фиксированной боковой панелью, мобильной нижней навигацией, 3D/glow карточками и сервисами.
- Fenix VPN: https://t.me/fenixVPNrobot
- Fenix Stars: https://t.me/Fenix_stars_bot
- Fenix Support: https://t.me/fenix_supportBot

Запуск локально Windows:
1) python -m venv .venv
2) .venv\\Scripts\\activate
3) pip install -r requirements.txt
4) set OWNER_PASSWORD=ChangeMe_123!
5) uvicorn main:app --reload --port 8000

Render:
Build: pip install -r requirements.txt
Start: uvicorn main:app --host 0.0.0.0 --port $PORT

Важно:
Текущий backend этой сборки использует SQLite. render.yaml подключает persistent disk /var/data, поэтому данные сохраняются на Render при наличии диска. Neon в эту сборку не подключён автоматически.

Банк вопросов:
При старте аттестации backend делает SELECT ... ORDER BY RANDOM() LIMIT 33 из активных вопросов. Поэтому если в базе 100 активных вопросов, конкретная попытка получает случайные 33 и сохраняет именно их в attempt_questions.
