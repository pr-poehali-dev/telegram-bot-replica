"""
Webhook-обработчик для Telegram бота FunStat.
Принимает обновления от Telegram, обрабатывает команды и сообщения.
"""

import json
import os
import requests
import psycopg2
from datetime import datetime

TELEGRAM_API = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}"
SCHEMA = os.environ.get("MAIN_DB_SCHEMA", "t_p73400739_telegram_bot_replica")


def get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)


def upsert_user(user: dict):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"""
        INSERT INTO {SCHEMA}.bot_users (id, username, first_name, last_name, language_code, last_seen)
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (id) DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_seen = NOW()
        """,
        (
            user.get("id"),
            user.get("username"),
            user.get("first_name"),
            user.get("last_name"),
            user.get("language_code"),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def log_query(user_id: int, query_type: str, query_value: str, result: dict):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"""
        INSERT INTO {SCHEMA}.bot_queries (user_id, query_type, query_value, result)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, query_type, query_value, json.dumps(result, ensure_ascii=False)),
    )
    conn.commit()
    cur.close()
    conn.close()


def analyze_user(username: str, chat_id: int, user_id: int):
    """Анализ Telegram пользователя по username"""
    username = username.lstrip("@").strip()
    if not username:
        send_message(chat_id, "❌ Укажи @username после команды.\nПример: <code>/analyze durov</code>")
        return

    send_message(chat_id, f"🔍 Анализирую <b>@{username}</b>...\n<i>Собираю публичные данные</i>")

    try:
        r = requests.get(
            f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/getChat",
            params={"chat_id": f"@{username}"},
            timeout=10,
        )
        data = r.json()

        if data.get("ok"):
            info = data["result"]
            chat_type = info.get("type", "")
            title = info.get("title") or info.get("first_name") or username
            description = info.get("description", "Нет описания")[:200]
            members = info.get("members_count", "—")
            user_type = "👤 Пользователь" if chat_type == "private" else "📢 Канал/Группа"

            text = (
                f"📊 <b>Профиль: @{username}</b>\n\n"
                f"{user_type}\n"
                f"<b>Название:</b> {title}\n"
                f"<b>Участников:</b> {members}\n\n"
                f"<b>Описание:</b>\n{description}\n\n"
                f"<i>🔒 Данные из публичных источников Telegram</i>"
            )
            result = {"username": username, "title": title, "members": members, "type": chat_type}
        else:
            text = (
                f"⚠️ <b>@{username}</b> не найден или профиль закрыт.\n\n"
                f"<i>FunStat анализирует только публичные профили и каналы.</i>"
            )
            result = {"username": username, "error": "not_found"}

        send_message(chat_id, text)
        log_query(user_id, "analyze", username, result)

    except Exception as e:
        send_message(chat_id, f"⚠️ Ошибка при анализе. Попробуй позже.")


def search_chats(query: str, chat_id: int, user_id: int):
    """Поиск публичных чатов и каналов"""
    query = query.strip()
    if not query:
        send_message(chat_id, "❌ Укажи запрос.\nПример: <code>/search python разработка</code>")
        return

    send_message(chat_id, f"🔎 Ищу чаты по запросу: <b>{query}</b>...")

    # Пробуем найти как username напрямую
    candidates = [query.replace(" ", "_"), query.replace(" ", ""), query.split()[0]]
    found = []

    for candidate in candidates:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/getChat",
                params={"chat_id": f"@{candidate}"},
                timeout=5,
            )
            data = r.json()
            if data.get("ok"):
                info = data["result"]
                found.append({
                    "username": candidate,
                    "title": info.get("title") or info.get("first_name", candidate),
                    "members": info.get("members_count", "—"),
                    "type": info.get("type", ""),
                })
        except Exception:
            pass

    if found:
        lines = [f"📋 <b>Найдено по запросу «{query}»:</b>\n"]
        for ch in found:
            emoji = "📢" if ch["type"] in ("channel", "supergroup", "group") else "👤"
            lines.append(f"{emoji} <b>{ch['title']}</b> @{ch['username']}\n   👥 {ch['members']} участн.\n")
        send_message(chat_id, "\n".join(lines))
    else:
        send_message(
            chat_id,
            f"😔 По запросу <b>{query}</b> публичные чаты не найдены.\n\n"
            f"<i>Попробуй точный @username канала или другое ключевое слово.</i>",
        )

    log_query(user_id, "search", query, {"found": len(found), "results": found})


def show_stats(chat_id: int, user_id: int):
    """Показать статистику пользователя в боте"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"SELECT COUNT(*) FROM {SCHEMA}.bot_queries WHERE user_id = %s", (user_id,)
    )
    total = cur.fetchone()[0]

    cur.execute(
        f"SELECT query_type, COUNT(*) FROM {SCHEMA}.bot_queries WHERE user_id = %s GROUP BY query_type",
        (user_id,),
    )
    by_type = cur.fetchall()
    cur.close()
    conn.close()

    lines = [f"📊 <b>Твоя статистика в FunStat</b>\n", f"Всего запросов: <b>{total}</b>\n"]
    type_names = {"analyze": "🔍 Анализ профилей", "search": "🔎 Поиск чатов"}
    for qt, cnt in by_type:
        lines.append(f"{type_names.get(qt, qt)}: <b>{cnt}</b>")

    conn2 = get_db()
    cur2 = conn2.cursor()
    cur2.execute(f"SELECT COUNT(DISTINCT id) FROM {SCHEMA}.bot_users")
    total_users = cur2.fetchone()[0]
    cur2.close()
    conn2.close()

    lines.append(f"\n👥 Всего пользователей бота: <b>{total_users}</b>")
    send_message(chat_id, "\n".join(lines))


def send_main_menu(chat_id: int, name: str):
    text = (
        f"👋 Привет, <b>{name}</b>!\n\n"
        f"🤖 <b>FunStat</b> — OSINT-аналитика Telegram\n\n"
        f"<b>Команды:</b>\n"
        f"🔍 /analyze @username — анализ профиля\n"
        f"🔎 /search запрос — поиск чатов\n"
        f"📊 /stats — твоя статистика\n"
        f"ℹ️ /help — справка\n\n"
        f"<i>Работаю только с публичными данными Telegram</i>"
    )
    keyboard = {
        "keyboard": [
            [{"text": "🔍 Анализ профиля"}, {"text": "🔎 Поиск чатов"}],
            [{"text": "📊 Статистика"}, {"text": "ℹ️ Помощь"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }
    send_message(chat_id, text, reply_markup=keyboard)


def send_help(chat_id: int):
    text = (
        "ℹ️ <b>Справка FunStat</b>\n\n"
        "<b>/analyze @username</b>\n"
        "Анализ публичного профиля, канала или группы: название, количество участников, описание.\n\n"
        "<b>/search запрос</b>\n"
        "Поиск публичных Telegram-чатов по ключевому слову или username.\n\n"
        "<b>/stats</b>\n"
        "Твоя личная статистика запросов в боте.\n\n"
        "⚠️ <b>Важно:</b> бот работает только с публичными данными Telegram. "
        "Приватные чаты и личные переписки недоступны.\n\n"
        "🛡️ Используй только в законных целях: OSINT, маркетинг, исследования."
    )
    send_message(chat_id, text)


def handler(event: dict, context) -> dict:
    """Основной webhook-обработчик входящих обновлений от Telegram"""

    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
            "body": "",
        }

    try:
        body = json.loads(event.get("body", "{}"))
    except Exception:
        return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": "ok"}

    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": "ok"}

    chat_id = message["chat"]["id"]
    user = message.get("from", {})
    user_id = user.get("id", chat_id)
    text = message.get("text", "").strip()
    name = user.get("first_name") or user.get("username") or "друг"

    # Сохраняем пользователя
    try:
        upsert_user(user)
    except Exception:
        pass

    # Обработка команд и кнопок меню
    if text in ("/start", "/menu"):
        send_main_menu(chat_id, name)

    elif text in ("/help", "ℹ️ Помощь"):
        send_help(chat_id)

    elif text in ("/stats", "📊 Статистика"):
        show_stats(chat_id, user_id)

    elif text.startswith("/analyze "):
        username = text[len("/analyze "):]
        analyze_user(username, chat_id, user_id)

    elif text == "🔍 Анализ профиля":
        send_message(
            chat_id,
            "🔍 Введи команду:\n<code>/analyze @username</code>\n\nНапример: <code>/analyze durov</code>"
        )

    elif text.startswith("/search "):
        query = text[len("/search "):]
        search_chats(query, chat_id, user_id)

    elif text == "🔎 Поиск чатов":
        send_message(
            chat_id,
            "🔎 Введи команду:\n<code>/search ключевое слово</code>\n\nНапример: <code>/search python</code>"
        )

    elif text == "/analyze":
        send_message(chat_id, "🔍 Укажи @username:\n<code>/analyze @username</code>")

    elif text == "/search":
        send_message(chat_id, "🔎 Укажи запрос:\n<code>/search ключевое слово</code>")

    else:
        send_message(
            chat_id,
            f"🤖 Привет! Я не понял команду.\n\nНапиши /help для справки или выбери кнопку ниже.",
        )

    return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": "ok"}
