#!/bin/bash
set -e

echo "[entrypoint] 等待 MongoDB 就绪..."

python - <<'PYEOF'
import os, time
from pymongo import MongoClient

host = os.environ.get("MONGO_HOST", "mongo")
port = int(os.environ.get("MONGO_PORT", "27017"))
user = os.environ.get("MONGO_USERNAME", "")
pwd = os.environ.get("MONGO_PASSWORD", "")
auth = os.environ.get("MONGO_AUTH_SOURCE", "admin")

for i in range(60):
    try:
        c = MongoClient(
            f"mongodb://{host}:{port}/",
            username=user, password=pwd,
            authSource=auth, serverSelectionTimeoutMS=2000,
        )
        c.admin.command("ping")
        c.close()
        print("[entrypoint] MongoDB 就绪")
        break
    except Exception as e:
        if i == 59:
            print(f"[entrypoint] MongoDB 连接失败: {e}")
            raise SystemExit(1)
        time.sleep(2)
PYEOF

echo "[entrypoint] 启动 MCP Server (端口 8090)..."
python /app/xhs_mcp_server.py &
MCP_PID=$!

echo "[entrypoint] 启动 NiceGUI 控制面板 (端口 8080)..."
python /app/nicegui_app.py &
WEB_PID=$!

trap "kill $MCP_PID $WEB_PID 2>/dev/null || true" SIGTERM SIGINT

wait -n
