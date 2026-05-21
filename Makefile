# Makefile

.PHONY: help db-up db-down migrate-new migrate-up migrate-down shell

include .env
export

DATABASE_URL := postgresql+psycopg2://max_bot_admin:$(ADMIN_PASSWORD)@localhost:5433/$(POSTGRES_DB)

help:
	@echo "Available commands:"
	@echo "  make db-up          - Start database"
	@echo "  make db-down        - Stop database"
	@echo "  make migrate-new    - Create new migration (msg=\"description\")"
	@echo "  make migrate-up     - Apply all pending migrations"
	@echo "  make migrate-down   - Rollback last migration"
	@echo "  make shell          - Enter database shell"

db-up:
	docker compose up -d db init-db

db-down:
	docker compose down -v

migrate-new:
	@read -p "Migration message: " msg; \
	export DATABASE_URL="$(DATABASE_URL)"; \
	alembic revision --autogenerate -m "$$msg"

migrate-up:
	docker compose run --rm migrations alembic upgrade head

migrate-down:
	docker compose run --rm migrations alembic downgrade -1

shell:
	docker exec -it max_bot_db psql -U max_bot_admin -d max_bot_db