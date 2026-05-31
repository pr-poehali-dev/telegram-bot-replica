"""
Утилита для регистрации Telegram webhook и получения статистики бота.
"""

import json
import os
import requests
import psycopg2

TELEGRAM_API = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}"
SCHEMA = os.environ.get("MAIN_DB_SCHEMA", "t_p73400739_telegram_bot_replica")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def handler(event: dict, context) -> dict:
    """Регистрирует webhook и отдаёт статистику бота для дашборда"""

    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    params = event.get("queryStringParameters") or {}
    action = params.get("action", "stats")

    if action == "set_webhook":
        webhook_url = params.get("url", "")
        if not webhook_url:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "url required"}),
            }
        r = requests.post(
            f"{TELEGRAM_API}/setWebhook",
            json={"url": webhook_url, "allowed_updates": ["message", "edited_message"]},
        )
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(r.json()),
        }

    if action == "get_webhook":
        r = requests.get(f"{TELEGRAM_API}/getWebhookInfo")
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(r.json()),
        }

    if action == "get_me":
        r = requests.get(f"{TELEGRAM_API}/getMe")
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(r.json()),
        }

    if action == "get_chat":
        username = params.get("username", "").strip().lstrip("@")
        if not username:
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"ok": False, "error": "username required"})}
        r = requests.get(f"{TELEGRAM_API}/getChat", params={"chat_id": f"@{username}"}, timeout=10)
        data = r.json()
        if data.get("ok") and data.get("result"):
            # Добавляем members_count для каналов/групп
            chat_id = data["result"].get("id")
            if data["result"].get("type") in ("channel", "supergroup", "group") and chat_id:
                mc = requests.get(f"{TELEGRAM_API}/getChatMemberCount", params={"chat_id": chat_id}, timeout=5).json()
                if mc.get("ok"):
                    data["result"]["members_count"] = mc["result"]
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps(data)}

    if action == "search":
        query = params.get("q", "").strip()
        candidates = [query.replace(" ", "_"), query.replace(" ", ""), query.split()[0] if query else ""]
        found = []
        for c in set(candidates):
            if not c:
                continue
            try:
                r = requests.get(f"{TELEGRAM_API}/getChat", params={"chat_id": f"@{c}"}, timeout=5)
                d = r.json()
                if d.get("ok") and d.get("result"):
                    info = d["result"]
                    mc = requests.get(f"{TELEGRAM_API}/getChatMemberCount", params={"chat_id": info["id"]}, timeout=5).json()
                    info["members_count"] = mc.get("result", "—")
                    found.append(info)
            except Exception:
                pass
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True, "results": found})}

    # По умолчанию — статистика для дашборда
    conn = get_db()
    cur = conn.cursor()

    cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.bot_users")
    total_users = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.bot_queries")
    total_queries = cur.fetchone()[0]

    cur.execute(
        f"SELECT COUNT(*) FROM {SCHEMA}.bot_queries WHERE created_at > NOW() - INTERVAL '24 hours'"
    )
    queries_24h = cur.fetchone()[0]

    cur.execute(
        f"SELECT COUNT(*) FROM {SCHEMA}.bot_users WHERE last_seen > NOW() - INTERVAL '24 hours'"
    )
    active_24h = cur.fetchone()[0]

    cur.execute(
        f"""
        SELECT query_type, COUNT(*) as cnt
        FROM {SCHEMA}.bot_queries
        GROUP BY query_type
        ORDER BY cnt DESC
        """
    )
    by_type = [{"type": row[0], "count": row[1]} for row in cur.fetchall()]

    cur.execute(
        f"""
        SELECT DATE_TRUNC('hour', created_at) as hour, COUNT(*) as cnt
        FROM {SCHEMA}.bot_queries
        WHERE created_at > NOW() - INTERVAL '24 hours'
        GROUP BY hour
        ORDER BY hour
        """
    )
    hourly = [{"hour": str(row[0]), "count": row[1]} for row in cur.fetchall()]

    cur.close()
    conn.close()

    bot_info = requests.get(f"{TELEGRAM_API}/getMe").json().get("result", {})

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({
            "bot": {
                "username": bot_info.get("username"),
                "first_name": bot_info.get("first_name"),
            },
            "stats": {
                "total_users": total_users,
                "total_queries": total_queries,
                "queries_24h": queries_24h,
                "active_users_24h": active_24h,
            },
            "by_type": by_type,
            "hourly": hourly,
        }),
    }