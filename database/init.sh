#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
while ! pg_isready -h db -U ${POSTGRES_USER}; do
    sleep 1
done

echo "PostgreSQL is ready. Executing init script..."

export PGPASSWORD=${POSTGRES_PASSWORD}
psql -h db -U ${POSTGRES_USER} -d ${POSTGRES_DB} <<EOF
DO \$\$
DECLARE
    admin_password text := '${ADMIN_PASSWORD}';
    user_password text := '${USER_PASSWORD}';
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'max_bot_admin') THEN
        EXECUTE 'CREATE USER max_bot_admin WITH PASSWORD ' || quote_literal(admin_password) || ' SUPERUSER';
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'max_bot_user') THEN
        EXECUTE 'CREATE USER max_bot_user WITH PASSWORD ' || quote_literal(user_password);
    END IF;
END \$\$;

CREATE SCHEMA IF NOT EXISTS bot_schema;

GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO max_bot_user;
GRANT USAGE ON SCHEMA bot_schema TO max_bot_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA bot_schema TO max_bot_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA bot_schema TO max_bot_user;

REVOKE CREATE ON SCHEMA bot_schema FROM max_bot_user;

ALTER DEFAULT PRIVILEGES FOR USER max_bot_admin IN SCHEMA bot_schema
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO max_bot_user;
ALTER DEFAULT PRIVILEGES FOR USER max_bot_admin IN SCHEMA bot_schema
    GRANT USAGE ON SEQUENCES TO max_bot_user;

ALTER ROLE max_bot_user SET search_path TO bot_schema, public;
EOF

echo "Init completed successfully"