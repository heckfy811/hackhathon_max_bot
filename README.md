# Архитектура проекта MAX Bot (Электронное бюро пропусков)

## Общее описание

Проект представляет собой чат-бота для мессенджера MAX, автоматизирующего оформление разовых гостевых пропусков в университете. Бот реализует ролевую модель (инициатор — администратор) и обеспечивает полный аудит действий.

## Технологический стек

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| Язык | Python 3.12 | Основной язык разработки |
| Фреймворк бота | maxapi | Библиотека для работы с MAX Bot API |
| ORM | SQLAlchemy 2.0 (async) | Работа с базой данных |
| Миграции | Alembic | Управление схемой БД |
| База данных | PostgreSQL 16 | Хранение данных |
| Контейнеризация | Docker + Docker Compose | Запуск и оркестрация |
| Управление зависимостями | pip + requirements.txt | Python-пакеты |

## Структура проекта

```
hackhathon_max_bot/
├── .env                      # Переменные окружения (не в Git)
├── .env.example              # Шаблон переменных окружения
├── .gitignore                # Исключаемые файлы
├── docker-compose.yml        # Оркестрация сервисов
├── Dockerfile                # Сборка образа бота
├── requirements.txt          # Python-зависимости
├── alembic.ini               # Конфиг Alembic для Docker
├── alembic.local.ini         # Конфиг Alembic для локального запуска (игнорится)
├── Makefile                  # Утилиты для разработки
│
├── database/                 # Всё для БД
│   ├── init.sh               # Скрипт инициализации БД (ждёт PostgreSQL)
│   └── migrations/           # Миграции Alembic
│       ├── env.py            # Конфигурация окружения для миграций
│       ├── script.py.mako    # Шаблон миграций
│       └── versions/         # Файлы миграций (коммитятся в Git)
│
├── src/                      # Исходный код бота
│   ├── __init__.py
│   ├── main.py               # Точка входа
│   ├── config.py             # Конфигурация из .env
│   ├── models/               # SQLAlchemy модели
│   │   ├── __init__.py       # Base и экспорт моделей
│   │   ├── user.py           # Пользователи
│   │   ├── request.py        # Заявки на пропуск
│   │   └── audit_log.py      # Аудит-лог
│   ├── repositories/         # Репозитории (CRUD)
│   ├── services/             # Бизнес-логика
│   ├── handlers/             # Обработчики команд бота
│   ├── keyboards/            # Клавиатуры (кнопки)
│   ├── fsm/                  # Машина состояний (диалоги)
│   ├── middleware/           # Прослойки (аутентификация, логи)
│   └── utils/                # Утилиты (валидаторы, форматтеры)
│
└── docs/                     # Документация
```

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