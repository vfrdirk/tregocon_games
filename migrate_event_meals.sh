#!/usr/bin/env bash
# Add event dates + meal label/volunteers columns (idempotent).
PSQL="docker exec -i tregocon-postgres-1 psql -U tregocon -d tregocon -v ON_ERROR_STOP=0"
for stmt in \
  "ALTER TABLE events ADD COLUMN IF NOT EXISTS event_start TIMESTAMP;" \
  "ALTER TABLE events ADD COLUMN IF NOT EXISTS event_end TIMESTAMP;" \
  "ALTER TABLE meal_options ADD COLUMN IF NOT EXISTS label VARCHAR;" \
  "ALTER TABLE meal_options ADD COLUMN IF NOT EXISTS volunteers TEXT DEFAULT '[]';"; do
  echo "$stmt" | $PSQL
done
echo "=== verify ==="
echo "SELECT column_name FROM information_schema.columns WHERE table_name='events' AND column_name IN ('event_start','event_end');" | $PSQL
echo "SELECT column_name FROM information_schema.columns WHERE table_name='meal_options' AND column_name IN ('label','volunteers');" | $PSQL
