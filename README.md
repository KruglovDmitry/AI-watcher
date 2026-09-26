# AI Watcher

Контроль смен сотрудников через Telegram-бота и админ-панель.

## Что умеет MVP

**Сотрудник (Telegram):**
- привязка по коду `/start КОД`
- кнопка **Я на смене** (с геолокацией, радиус точки до 500 м)
- кнопка **Закончил работу** (ранний уход)
- **Статус смены** / таймер до конца графика
- напоминание за 15 минут до начала
- авто-закрытие смены по окончании графика
- утренняя проверка в 10:00 (нет check-in → алерт админу и сотруднику)

**Админ (веб):**
- дашборд статусов на день
- сотрудники с алиасами и invite-кодами
- точки (координаты + радиус)
- график смен
- лента алертов

## Стек

- Backend: Python, FastAPI, SQLAlchemy, python-telegram-bot, APScheduler
- DB: PostgreSQL
- Admin: React + Vite + Ant Design (паттерны как в AI-booking)

## Быстрый старт

1. Скопируйте env:

```bash
cp .env.example .env
```

2. Укажите `TELEGRAM_BOT_TOKEN` (и опционально `ADMIN_TELEGRAM_CHAT_ID`).

3. Запуск через Docker:

```bash
docker compose up --build
```

- API: http://localhost:8001/docs  
- Админка: http://localhost:3001  
- Логин по умолчанию: `admin` / `admin`

> Порты `8001` и `3001`, потому что `8000`/`3000` часто заняты другими проектами.

Если бот не поднимается (`bot_ready: false` в `/health`) — из Docker нет доступа к `api.telegram.org`.
Варианты: VPN на хосте + `network_mode: host` для backend, либо `TELEGRAM_PROXY_URL` в `.env`.

## Локальная разработка

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
# поднимите Postgres (docker compose up db -d)
set PYTHONPATH=.
uvicorn app.main:app --reload --port 8000
```

### Admin

```bash
cd admin
npm install
npm run dev
```

Админка: http://localhost:5173 (проксирует `/api` на backend).

## Сценарий первого дня

1. Войти в админку.
2. Создать точку с координатами и радиусом.
3. Создать сотрудника → скопировать код.
4. Сотрудник пишет боту: `/start КОД`.
5. В «График» назначить смену на сегодня.
6. На точке нажать «Я на смене».

## Дальше (не в MVP)

- периодическая проверка геопозиции с интервалом
- экспорт отчётов
- роли админов / несколько организаций
