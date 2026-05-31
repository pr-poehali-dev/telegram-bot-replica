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
