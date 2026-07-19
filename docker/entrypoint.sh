#!/usr/bin/env bash
set -euo pipefail

echo "Warte auf Datenbank..."
python - <<'PYEOF'
import os
import sys
import time

import psycopg2

url = os.environ.get("DATABASE_URL")
if not url:
    sys.exit("DATABASE_URL ist nicht gesetzt")

for _ in range(30):
    try:
        conn = psycopg2.connect(url)
        conn.close()
        break
    except psycopg2.OperationalError:
        time.sleep(2)
else:
    sys.exit("Datenbank nach 60 Sekunden nicht erreichbar")
PYEOF

echo "Fuehre Datenbankmigrationen aus..."
flask db upgrade

exec "$@"
