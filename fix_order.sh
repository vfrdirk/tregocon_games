#!/usr/bin/env bash
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i /opt/data/Hermes_Dirk.pem ubuntu@32.199.228.225 "cd /opt/tregocon && sudo git fetch origin && sudo git reset --hard origin/main >/dev/null 2>&1 && sudo docker compose -f docker-compose.prod.yml --env-file .env up -d --build backend 2>&1 | tail -2"
sleep 5
echo "=== API order after rebuild ==="
curl -sS --max-time 10 https://play.tregocon.games/api/meals | python3 -c 'import sys,json; d=json.load(sys.stdin); print([s["service"] for s in d["services"]])'
echo "=== simulate a SAVE (UPDATE meal 8 = fri_dinner) like the Config editor does ==="
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i /opt/data/Hermes_Dirk.pem ubuntu@32.199.228.225 "sudo docker exec -i tregocon-postgres-1 psql -U tregocon -d tregocon -c \"UPDATE meal_options SET label='Friday Dinner' WHERE id=8;\" >/dev/null"
echo "=== API order AFTER the UPDATE (should still be chronological) ==="
curl -sS --max-time 10 https://play.tregocon.games/api/meals | python3 -c 'import sys,json; d=json.load(sys.stdin); print([s["service"] for s in d["services"]])'
echo "=== revert the test label ==="
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i /opt/data/Hermes_Dirk.pem ubuntu@32.199.228.225 "sudo docker exec -i tregocon-postgres-1 psql -U tregocon -d tregocon -c \"UPDATE meal_options SET label=NULL WHERE id=8;\" >/dev/null"
