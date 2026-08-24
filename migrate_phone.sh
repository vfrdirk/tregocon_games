#!/usr/bin/env bash
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i /opt/data/Hermes_Dirk.pem ubuntu@32.199.228.225 "sudo docker exec -i tregocon-postgres-1 psql -U tregocon -d tregocon -c \"ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR;\" && echo 'phone column OK'"
