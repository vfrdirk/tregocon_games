#!/usr/bin/env bash
# Add sms_opt_in column (explicit SMS consent; never default-on) to users.
# Run on the postgres container. Safe to re-run (IF NOT EXISTS).
set -e
PG="postgresql://tregocon:${POSTGRES_PASSWORD}@postgres:5432/tregocon"
psql "$PG" -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS sms_opt_in BOOLEAN DEFAULT FALSE;"
psql "$PG" -c "UPDATE users SET sms_opt_in = FALSE WHERE sms_opt_in IS NULL;"
echo "migration: sms_opt_in/in column ensured"
