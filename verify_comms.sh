#!/usr/bin/env bash
set -e
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i /opt/data/Hermes_Dirk.pem ubuntu@32.199.228.225 "cd /opt/tregocon && sudo git fetch origin && sudo git reset --hard origin/main && sudo docker exec -i tregocon-postgres-1 psql -U tregocon -d tregocon -c \"ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR;\" && sudo docker compose -f docker-compose.prod.yml --env-file .env up -d --build backend frontend 2>&1 | tail -3"
sleep 5
echo "=== comms status (creds present?) ==="
curl -sS --max-time 10 https://play.tregocon.games/api/admin/event/comms-status -b /tmp/nope 2>/dev/null | head -c 120 || echo "(needs auth, expected)"
echo
echo "=== verify /me returns phone field (admin) ==="
TOK="tmp$(date +%s)"
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i /opt/data/Hermes_Dirk.pem ubuntu@32.199.228.225 "sudo docker exec -i tregocon-postgres-1 psql -U tregocon -d tregocon -c \"INSERT INTO sessions(token, user_id) VALUES ('$TOK', 1);\"" >/dev/null
curl -sS --max-time 10 https://play.tregocon.games/api/auth/me -H "Cookie: tregocon_session=$TOK" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("phone field present:", "phone" in d, "| value:", d.get("phone"))'
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i /opt/data/Hermes_Dirk.pem ubuntu@32.199.228.225 "sudo docker exec -i tregocon-postgres-1 psql -U tregocon -d tregocon -c \"DELETE FROM sessions WHERE token='$TOK';\""
curl -sS --max-time 10 -o /dev/null -w 'site https=%{http_code}\n' https://play.tregocon.games/
