"""
Webhook-обработчик FunStat бота — анализ публичных каналов и групп Telegram.
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


def send(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
    except Exception:
        pass


def answer_cb(callback_id):
    try:
        requests.post(f"{TELEGRAM_API}/answerCallbackQuery",
                      json={"callback_query_id": callback_id}, timeout=5)
    except Exception:
        pass


def upsert_user(user: dict):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            f"""INSERT INTO {SCHEMA}.bot_users (id, username, first_name, last_name, language_code, last_seen)
                VALUES (%s,%s,%s,%s,%s,NOW())
                ON CONFLICT (id) DO UPDATE SET username=EXCLUDED.username,
                first_name=EXCLUDED.first_name, last_seen=NOW()""",
            (user.get("id"), user.get("username"), user.get("first_name"),
             user.get("last_name"), user.get("language_code")),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


def log_query(user_id, query_type, query_value, result):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO {SCHEMA}.bot_queries (user_id,query_type,query_value,result) VALUES (%s,%s,%s,%s)",
            (user_id, query_type, query_value, json.dumps(result, ensure_ascii=False)),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


def get_chat_full(username: str) -> dict:
    """Получить полные данные канала/группы"""
    username = username.lstrip("@").strip()
    r = requests.get(f"{TELEGRAM_API}/getChat",
                     params={"chat_id": f"@{username}"}, timeout=10)
    data = r.json()
    if not data.get("ok"):
        return {}
    info = data["result"]
    chat_id = info["id"]

    # Количество участников
    mc = requests.get(f"{TELEGRAM_API}/getChatMemberCount",
                      params={"chat_id": chat_id}, timeout=5).json()
    if mc.get("ok"):
        info["members_count"] = mc["result"]

    # Администраторы
    admins = requests.get(f"{TELEGRAM_API}/getChatAdministrators",
                          params={"chat_id": chat_id}, timeout=8).json()
    if admins.get("ok"):
        info["admins"] = admins["result"]

    return info


def format_num(n) -> str:
    if n is None:
        return "—"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def analyze_channel(username: str, chat_id: int, user_id: int):
    """Полный анализ публичного канала или группы"""
    username = username.lstrip("@").strip()
    if not username:
        send(chat_id, "❌ Укажи @username канала.\nПример: <code>@telegram</code>")
        return

    send(chat_id, f"🔍 Анализирую <b>@{username}</b>...\n<i>Собираю данные</i>")

    info = get_chat_full(username)

    if not info:
        send(chat_id,
             f"⚠️ <b>@{username}</b> не найден.\n\n"
             f"Убедись что:\n"
             f"• Это публичный канал или группа\n"
             f"• @username написан правильно\n\n"
             f"<b>Примеры для проверки:</b>\n"
             f"@telegram · @durov · @python")
        log_query(user_id, "analyze", username, {"error": "not_found"})
        return

    ctype = info.get("type", "")
    title = info.get("title", username)
    uname = info.get("username", username)
    members = info.get("members_count")
    description = (info.get("description") or "").strip()
    tg_id = info.get("id", "")
    admins = info.get("admins", [])
    is_verified = info.get("is_verified", False)
    is_scam = info.get("is_scam", False)
    is_fake = info.get("is_fake", False)
    slow_mode = info.get("slow_mode_delay")
    has_protected = info.get("has_protected_content", False)
    linked_chat = info.get("linked_chat_id")
    invite_link = info.get("invite_link", "")

    type_map = {"channel": "📢 Канал", "supergroup": "👥 Супергруппа", "group": "👥 Группа"}
    type_label = type_map.get(ctype, "❓ Неизвестно")

    status_parts = []
    if is_verified:
        status_parts.append("✅ Верифицирован")
    if is_scam:
        status_parts.append("🚨 SCAM")
    if is_fake:
        status_parts.append("⚠️ FAKE")
    if has_protected:
        status_parts.append("🔒 Защита контента")
    status_line = " · ".join(status_parts) if status_parts else "✅ Обычный"

    admin_bots = sum(1 for a in admins if a.get("user", {}).get("is_bot"))
    admin_count = len(admins)

    lines = [
        f"{'📢' if ctype == 'channel' else '👥'} <b>{title}</b>",
        f"@{uname}  ·  {type_label}",
        "",
        f"👥 Участников: <b>{format_num(members)}</b>",
        f"🆔 ID: <code>{tg_id}</code>",
        f"📋 Статус: {status_line}",
    ]

    if admin_count:
        lines.append(f"👑 Админов: <b>{admin_count}</b>" +
                     (f" (ботов: {admin_bots})" if admin_bots else ""))

    if slow_mode:
        lines.append(f"🐢 Медленный режим: {slow_mode}с")

    if linked_chat:
        lines.append(f"🔗 Связан с: <code>{linked_chat}</code>")

    if description:
        lines.append(f"\n📝 <b>Описание:</b>\n{description[:400]}")

    if invite_link and not invite_link.endswith(uname):
        lines.append(f"\n🔗 {invite_link}")

    lines.append(f"\n<i>Данные из публичного Telegram API</i>")

    buttons = {
        "inline_keyboard": [
            [
                {"text": "👑 Администраторы", "callback_data": f"admins:{uname}"},
                {"text": "🔄 Обновить", "callback_data": f"analyze:{uname}"},
            ],
            [{"text": "📊 Моя статистика", "callback_data": "botstats"}],
        ]
    }

    send(chat_id, "\n".join(lines), reply_markup=buttons)
    log_query(user_id, "analyze", username,
              {"title": title, "members": members, "type": ctype, "admins": admin_count})


def show_admins(username: str, chat_id: int):
    """Список администраторов канала"""
    username = username.lstrip("@").strip()
    info = get_chat_full(username)
    if not info:
        send(chat_id, "⚠️ Канал не найден")
        return

    admins = info.get("admins", [])
    title = info.get("title", username)

    if not admins:
        send(chat_id, f"👑 У <b>{title}</b> нет публичных администраторов.")
        return

    lines = [f"👑 <b>Администраторы @{username}</b> ({len(admins)}):\n"]
    for a in admins[:20]:
        u = a.get("user", {})
        fname = u.get("first_name", "")
        lname = u.get("last_name", "")
        full_name = (fname + (" " + lname if lname else "")).strip()
        uname_a = u.get("username", "")
        status = a.get("status", "")
        custom = a.get("custom_title", "")
        role_map = {"creator": "👑 Создатель", "administrator": "⚙️ Админ"}
        role = role_map.get(status, status)
        if custom:
            role += f" · {custom}"
        is_bot = "🤖 " if u.get("is_bot") else ""
        lines.append(
            f"{is_bot}<b>{full_name}</b>" +
            (f" @{uname_a}" if uname_a else "") +
            f"\n  └ {role}\n"
        )

    send(chat_id, "\n".join(lines))


def show_stats_bot(chat_id: int, user_id: int):
    """Статистика использования бота"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.bot_queries WHERE user_id=%s", (user_id,))
        my_total = cur.fetchone()[0]
        cur.execute(
            f"SELECT query_type, COUNT(*) FROM {SCHEMA}.bot_queries WHERE user_id=%s GROUP BY query_type",
            (user_id,))
        by_type = cur.fetchall()
        cur.execute(f"SELECT COUNT(DISTINCT id) FROM {SCHEMA}.bot_users")
        total_users = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.bot_queries")
        total_q = cur.fetchone()[0]
        cur.execute(
            f"SELECT query_value, COUNT(*) as c FROM {SCHEMA}.bot_queries "
            f"WHERE query_type='analyze' GROUP BY query_value ORDER BY c DESC LIMIT 5")
        top = cur.fetchall()
        cur.close()
        conn.close()
    except Exception:
        send(chat_id, "⚠️ Ошибка загрузки статистики")
        return

    type_names = {"analyze": "🔍 Анализов", "search": "🔎 Поисков"}
    lines = ["📊 <b>Статистика FunStat</b>\n",
             f"Твои запросы: <b>{my_total}</b>"]
    for qt, cnt in by_type:
        lines.append(f"  {type_names.get(qt, qt)}: {cnt}")
    lines.append(f"\n🌐 Всего пользователей: <b>{total_users}</b>")
    lines.append(f"📈 Всего запросов: <b>{total_q}</b>")
    if top:
        lines.append(f"\n🔥 <b>Топ каналов:</b>")
        for val, cnt in top:
            lines.append(f"  @{val} — {cnt} запр.")

    send(chat_id, "\n".join(lines))


def send_main_menu(chat_id: int, name: str):
    text = (
        f"👋 Привет, <b>{name}</b>!\n\n"
        f"🤖 <b>FunStat</b> — анализ Telegram каналов и групп\n\n"
        f"Отправь <b>@username</b> канала или группы:\n\n"
        f"<b>Примеры:</b>\n"
        f"@telegram · @durov · @python\n\n"
        f"🔍 /analyze @username — анализ\n"
        f"📊 /stats — статистика\n"
        f"ℹ️ /help — справка"
    )
    keyboard = {
        "keyboard": [
            [{"text": "🔍 Анализ канала"}, {"text": "📊 Статистика"}],
            [{"text": "ℹ️ Помощь"}],
        ],
        "resize_keyboard": True,
    }
    send(chat_id, text, reply_markup=keyboard)


def send_help(chat_id: int):
    send(chat_id,
         "ℹ️ <b>FunStat — анализ каналов Telegram</b>\n\n"
         "Просто отправь <b>@username</b> канала или группы:\n\n"
         "• 👥 Количество участников\n"
         "• 📋 Тип, ID, статус\n"
         "• 👑 Список администраторов\n"
         "• 📝 Описание канала\n"
         "• 🔒 Настройки безопасности\n\n"
         "<b>Примеры:</b>\n@telegram · @durov · @python\n\n"
         "⚠️ Работает только с публичными каналами и группами.")


def handle_callback(cb: dict, user_id: int):
    answer_cb(cb["id"])
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")

    if data.startswith("analyze:"):
        analyze_channel(data.split(":", 1)[1], chat_id, user_id)
    elif data.startswith("admins:"):
        show_admins(data.split(":", 1)[1], chat_id)
    elif data == "botstats":
        show_stats_bot(chat_id, user_id)


def handler(event: dict, context) -> dict:
    """Основной webhook-обработчик Telegram бота FunStat"""

    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200,
                "headers": {"Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                            "Access-Control-Allow-Headers": "Content-Type"},
                "body": ""}

    try:
        body = json.loads(event.get("body", "{}"))
    except Exception:
        return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": "ok"}

    if body.get("callback_query"):
        cb = body["callback_query"]
        handle_callback(cb, cb["from"]["id"])
        return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": "ok"}

    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": "ok"}

    chat_id = message["chat"]["id"]
    user = message.get("from", {})
    user_id = user.get("id", chat_id)
    text = message.get("text", "").strip()
    name = user.get("first_name") or user.get("username") or "друг"

    upsert_user(user)

    if text in ("/start", "/menu"):
        send_main_menu(chat_id, name)
    elif text in ("/help", "ℹ️ Помощь"):
        send_help(chat_id)
    elif text in ("/stats", "📊 Статистика"):
        show_stats_bot(chat_id, user_id)
    elif text.startswith("/analyze "):
        analyze_channel(text[len("/analyze "):], chat_id, user_id)
    elif text == "/analyze":
        send(chat_id, "🔍 Укажи @username:\n<code>/analyze telegram</code>")
    elif text == "🔍 Анализ канала":
        send(chat_id, "🔍 Отправь @username канала.\n\nПример: <code>@telegram</code>")
    elif re.match(r'^@[\w]{3,}$', text):
        analyze_channel(text, chat_id, user_id)
    else:
        send(chat_id,
             "🤖 Отправь <b>@username</b> канала или группы.\n\n"
             "<b>Примеры:</b> @telegram · @durov · @python")

    return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": "ok"}
