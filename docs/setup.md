# Настройка окружения для разработки

## Требования

- Docker и Docker Compose
- Python 3.12+
- Git
- PostgreSQL (только для локальных миграций, можно использовать Docker)

## Первоначальная настройка

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-repo/hackhathon_max_bot.git
cd hackhathon_max_bot
```

### 2. Настройка переменных окружения

```bash
cp .env.example .env
# Отредактируйте .env:
# - При необходимости смените пароли ADMIN_PASSWORD/USER_PASSWORD
```

### 3. Запуск через Docker (рекомендуется)

```bash
# Поднять все сервисы (БД, init-db, миграции, бота)
docker compose up -d

# Проверить статус
docker compose ps

# Посмотреть логи
docker compose logs -f bot
```

### 4. Локальная разработка (создание миграций)

```bash
# Активировать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Установить зависимости
pip install -r requirements.txt

# Убедиться, что БД запущена
docker compose up -d db

# Создать новую миграцию после изменения моделей
alembic -c alembic.local.ini revision --autogenerate -m "описание_изменений"

# Применить миграцию (через Docker)
docker compose run --rm migrations alembic upgrade head
```

## Команды для управления

| Действие | Команда |
|----------|---------|
| Запуск всех сервисов | `docker compose up -d` |
| Остановка (данные сохраняются) | `docker compose stop` |
| Запуск после остановки | `docker compose start` |
| Перезапуск | `docker compose restart` |
| Полный сброс (удаление всех данных) | `docker compose down -v` |
| Просмотр логов бота | `docker compose logs -f bot` |
| Подключение к БД (через psql) | `psql -h localhost -p 5433 -U max_bot_user -d max_bot_db` |
| Пересборка образа бота | `docker compose build bot` |

## Работа с миграциями

### Создание новой миграции (локально)

```bash
# Убедиться, что БД запущена
docker compose up -d db

# Создать миграцию
alembic -c alembic.local.ini revision --autogenerate -m "add_new_field"
```

### Применение миграций (через Docker)

```bash
docker compose run --rm migrations alembic upgrade head
```

### Откат миграции

```bash
docker compose run --rm migrations alembic downgrade -1
```

### Просмотр истории миграций

```bash
docker compose run --rm migrations alembic history
```

## Устранение неполадок

### Бот не отвечает

```bash
# Проверить логи
docker compose logs bot
# Убедиться, что BOT_TOKEN корректен в .env
```

### Ошибка подключения к БД

```bash
# Проверить статус контейнера
docker compose ps
# Проверить логи БД
docker compose logs db
```

### Миграции не применяются

```bash
# Удалить кэш миграций
rm -rf database/migrations/versions/__pycache__
# Пересобрать образ migrations
docker compose build --no-cache migrations
# Применить заново
docker compose run --rm migrations alembic upgrade head
```

## Примечания

- **Никогда не коммитьте `.env`** — он содержит секреты.
- **Все миграции коммитятся в Git** — для синхронизации схемы между разработчиками.
- **Для production** используйте управляемую БД и не храните пароли в коде.
