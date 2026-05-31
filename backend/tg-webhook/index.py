"""
Webhook-обработчик для Telegram бота FunStat.
Принимает обновления от Telegram, обрабатывает команды и сообщения.
"""

import json
import os
import re
import requests
import psycopg2

TELEGRAM_API = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}"
SCHEMA = os.environ.get("MAIN_DB_SCHEMA", "t_p73400739_telegram_bot_replica")


def get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)


def send_message_with_buttons(chat_id, text, inline_buttons):
    """Отправить сообщение с inline-кнопками"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps({"inline_keyboard": inline_buttons}),
    }
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)


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
        (user.get("id"), user.get("username"), user.get("first_name"),
         user.get("last_name"), user.get("language_code")),
    )
    conn.commit()
    cur.close()
    conn.close()


def log_query(user_id: int, query_type: str, query_value: str, result: dict):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO {SCHEMA}.bot_queries (user_id, query_type, query_value, result) VALUES (%s, %s, %s, %s)",
        (user_id, query_type, query_value, json.dumps(result, ensure_ascii=False)),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_chat_info(username: str) -> dict:
    """Получить информацию о чате/канале через Bot API"""
    username = username.lstrip("@").strip()
    r = requests.get(f"{TELEGRAM_API}/getChat", params={"chat_id": f"@{username}"}, timeout=10)
    data = r.json()
    if data.get("ok") and data.get("result"):
        info = data["result"]
        # Получаем количество участников
        mc = requests.get(f"{TELEGRAM_API}/getChatMemberCount", params={"chat_id": info["id"]}, timeout=5).json()
        if mc.get("ok"):
            info["members_count"] = mc["result"]
        return info
    return {}


def analyze_user(username: str, chat_id: int, user_id: int):
    """Анализ Telegram пользователя/канала по username"""
    username = username.lstrip("@").strip()
    if not username:
        send_message(chat_id, "❌ Укажи @username.\nПример: <code>/analyze durov</code>")
        return

    send_message(chat_id, f"🔍 Анализирую <b>@{username}</b>...\n<i>Собираю данные из Telegram</i>")

    try:
        info = get_chat_info(username)

        if not info:
            send_message(
                chat_id,
                f"⚠️ <b>@{username}</b> не найден.\n\n"
                f"Убедись что:\n"
                f"• username написан правильно\n"
                f"• профиль или канал публичный\n\n"
                f"<i>Приватные аккаунты недоступны через Bot API.</i>"
            )
            log_query(user_id, "analyze", username, {"error": "not_found"})
            return

        chat_type = info.get("type", "")
        title = info.get("title") or f"{info.get('first_name', '')} {info.get('last_name', '')}".strip() or username
        uname = info.get("username", username)
        members = info.get("members_count")
        description = (info.get("description") or info.get("bio") or "").strip()
        chat_id_tg = info.get("id", "")
        linked = info.get("linked_chat_id")

        # Тип
        type_map = {
            "channel": "📢 Канал",
            "supergroup": "👥 Супергруппа",
            "group": "👥 Группа",
            "private": "👤 Пользователь",
        }
        type_label = type_map.get(chat_type, "❓ Неизвестно")

        # Формируем красивый ответ как у FunStat
        lines = [f"👤 <b>{title}</b>  @{uname}\n"]
        lines.append(f"{type_label}")
        if members is not None:
            lines.append(f"👥 Участников: <b>{members:,}</b>".replace(",", " "))
        lines.append(f"🆔 ID: <code>{chat_id_tg}</code>")

        if description:
            lines.append(f"\n📝 <b>Описание:</b>\n{description[:300]}")

        if info.get("invite_link"):
            lines.append(f"\n🔗 {info['invite_link']}")

        if linked:
            lines.append(f"🔗 Связанный чат: <code>{linked}</code>")

        # Дополнительные поля
        extras = []
        if info.get("slow_mode_delay"):
            extras.append(f"🐢 Медленный режим: {info['slow_mode_delay']}с")
        if info.get("has_protected_content"):
            extras.append("🔒 Защита контента")
        if info.get("is_verified"):
            extras.append("✅ Верифицирован")
        if info.get("is_scam"):
            extras.append("⚠️ SCAM аккаунт")
        if info.get("is_fake"):
            extras.append("⚠️ FAKE аккаунт")
        if extras:
            lines.append("\n" + " · ".join(extras))

        lines.append(f"\n<i>🔒 Публичные данные Telegram API</i>")

        text = "\n".join(lines)

        # Inline кнопки как у FunStat
        buttons = []
        if chat_type in ("channel", "supergroup", "group"):
            buttons = [[
                {"text": "🔎 Похожие каналы", "callback_data": f"similar:{uname}"},
                {"text": "📊 Статистика", "callback_data": f"chatstats:{uname}"},
            ]]
        else:
            buttons = [[
                {"text": "🔍 Анализ ещё", "callback_data": f"analyze:{uname}"},
            ]]

        send_message_with_buttons(chat_id, text, buttons)
        log_query(user_id, "analyze", username, {"title": title, "members": members, "type": chat_type})

    except Exception as e:
        send_message(chat_id, f"⚠️ Ошибка при анализе: {str(e)[:100]}")


def search_chats(query: str, chat_id: int, user_id: int):
    """Поиск публичных чатов и каналов"""
    query = query.strip().lstrip("@")
    if not query:
        send_message(chat_id, "❌ Укажи запрос.\nПример: <code>/search python</code>")
        return

    send_message(chat_id, f"🔎 Ищу: <b>@{query}</b>...")

    info = get_chat_info(query)
    if info:
        # Нашли — сразу показываем как analyze
        analyze_user(query, chat_id, user_id)
        return

    # Пробуем варианты
    candidates = list(set([
        query.replace(" ", "_"),
        query.replace(" ", ""),
        query.lower().replace(" ", "_"),
    ]))
    found = []
    for c in candidates:
        if c == query:
            continue
        i = get_chat_info(c)
        if i:
            found.append(i)

    if found:
        lines = [f"📋 <b>Результаты поиска «{query}»:</b>\n"]
        for ch in found:
            t = ch.get("title") or ch.get("first_name", "?")
            u = ch.get("username", "")
            m = ch.get("members_count")
            tp = {"channel": "📢", "supergroup": "👥", "group": "👥"}.get(ch.get("type", ""), "👤")
            lines.append(f"{tp} <b>{t}</b>" + (f" @{u}" if u else "") + (f"\n   👥 {m:,} участн.".replace(",", " ") if m else "") + "\n")
        send_message(chat_id, "\n".join(lines))
    else:
        send_message(
            chat_id,
            f"😔 По запросу <b>@{query}</b> ничего не найдено.\n\n"
            f"<i>Укажи точный @username публичного канала или группы.</i>"
        )

    log_query(user_id, "search", query, {"found": len(found)})


def show_stats(chat_id: int, user_id: int):
    """Показать статистику пользователя в боте"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.bot_queries WHERE user_id = %s", (user_id,))
    total = cur.fetchone()[0]
    cur.execute(f"SELECT query_type, COUNT(*) FROM {SCHEMA}.bot_queries WHERE user_id = %s GROUP BY query_type", (user_id,))
    by_type = cur.fetchall()
    cur.execute(f"SELECT COUNT(DISTINCT id) FROM {SCHEMA}.bot_users")
    total_users = cur.fetchone()[0]
    cur.close()
    conn.close()

    type_names = {"analyze": "🔍 Анализов профилей", "search": "🔎 Поисков чатов"}
    lines = [
        f"📊 <b>Твоя статистика FunStat</b>\n",
        f"Запросов выполнено: <b>{total}</b>",
    ]
    for qt, cnt in by_type:
        lines.append(f"{type_names.get(qt, qt)}: <b>{cnt}</b>")
    lines.append(f"\n👥 Всего в боте: <b>{total_users}</b> пользователей")
    send_message(chat_id, "\n".join(lines))


def send_main_menu(chat_id: int, name: str):
    text = (
        f"👋 Привет, <b>{name}</b>!\n\n"
        f"🤖 <b>FunStat</b> — OSINT-аналитика Telegram\n\n"
        f"Отправь <b>@username</b> или выбери действие:\n\n"
        f"🔍 /analyze @username — анализ профиля/канала\n"
        f"🔎 /search @username — поиск чата\n"
        f"📊 /stats — твоя статистика\n"
        f"ℹ️ /help — справка"
    )
    keyboard = {
        "keyboard": [
            [{"text": "🔍 Анализ профиля"}, {"text": "🔎 Поиск чатов"}],
            [{"text": "📊 Статистика"}, {"text": "ℹ️ Помощь"}],
        ],
        "resize_keyboard": True,
    }
    send_message(chat_id, text, reply_markup=keyboard)


def send_help(chat_id: int):
    text = (
        "ℹ️ <b>Справка FunStat</b>\n\n"
        "Просто отправь <b>@username</b> — и я сразу проанализирую.\n\n"
        "<b>/analyze @username</b> — анализ профиля, канала или группы\n"
        "<b>/search @username</b> — поиск публичного чата\n"
        "<b>/stats</b> — твоя статистика запросов\n\n"
        "📌 <b>Что показывает анализ:</b>\n"
        "• Название, тип, ID\n"
        "• Количество участников\n"
        "• Описание\n"
        "• Статус верификации / скам\n\n"
        "⚠️ Работает только с <b>публичными</b> данными Telegram.\n"
        "🛡️ Используй в законных целях: OSINT, маркетинг, исследования."
    )
    send_message(chat_id, text)


def handle_callback(callback: dict):
    """Обработка нажатий на inline-кнопки"""
    chat_id = callback["message"]["chat"]["id"]
    user_id = callback["from"]["id"]
    data = callback.get("data", "")

    # Отвечаем на callback чтобы убрать часики
    requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={"callback_query_id": callback["id"]}, timeout=5)

    if data.startswith("analyze:"):
        username = data.split(":", 1)[1]
        analyze_user(username, chat_id, user_id)
    elif data.startswith("similar:") or data.startswith("chatstats:"):
        username = data.split(":", 1)[1]
        send_message(chat_id, f"🔍 Анализирую <b>@{username}</b>...", )
        analyze_user(username, chat_id, user_id)


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

    # Обработка callback_query (нажатие inline-кнопок)
    if body.get("callback_query"):
        handle_callback(body["callback_query"])
        return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": "ok"}

    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": "ok"}

    chat_id = message["chat"]["id"]
    user = message.get("from", {})
    user_id = user.get("id", chat_id)
    text = message.get("text", "").strip()
    name = user.get("first_name") or user.get("username") or "друг"

    try:
        upsert_user(user)
    except Exception:
        pass

    # Обработка команд и сообщений
    if text in ("/start", "/menu"):
        send_main_menu(chat_id, name)

    elif text in ("/help", "ℹ️ Помощь"):
        send_help(chat_id)

    elif text in ("/stats", "📊 Статистика"):
        show_stats(chat_id, user_id)

    elif text.startswith("/analyze "):
        analyze_user(text[len("/analyze "):], chat_id, user_id)

    elif text == "/analyze":
        send_message(chat_id, "🔍 Укажи @username:\n<code>/analyze durov</code>")

    elif text.startswith("/search "):
        search_chats(text[len("/search "):], chat_id, user_id)

    elif text == "/search":
        send_message(chat_id, "🔎 Укажи @username или слово:\n<code>/search durov</code>")

    elif text == "🔍 Анализ профиля":
        send_message(chat_id, "🔍 Отправь @username для анализа.\nНапример: <code>@durov</code>")

    elif text == "🔎 Поиск чатов":
        send_message(chat_id, "🔎 Отправь @username канала или группы.\nНапример: <code>@telegram</code>")

    # ✅ ГЛАВНОЕ ИСПРАВЛЕНИЕ: если просто написали @username — сразу анализируем
    elif re.match(r'^@[\w]{3,}$', text):
        analyze_user(text, chat_id, user_id)

    # Если написали username без @ (если похоже на username)
    elif re.match(r'^[\w]{4,32}$', text) and '_' in text:
        analyze_user(text, chat_id, user_id)

    else:
        send_message(
            chat_id,
            f"🤖 Не понял команду.\n\n"
            f"Отправь <b>@username</b> для анализа или напиши /help"
        )

    return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": "ok"}
