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

## Схема базы данных

```sql
-- Схема bot_schema

-- Пользователи бота
CREATE TABLE bot_schema.users (
    max_user_id      VARCHAR(255) PRIMARY KEY,
    display_name     VARCHAR(255) NOT NULL,
    consent_given    BOOLEAN DEFAULT FALSE,
    consent_version  VARCHAR(50),
    consent_timestamp TIMESTAMP,
    role             VARCHAR(50) DEFAULT 'user',
    created_at       TIMESTAMP DEFAULT NOW()
);

-- Заявки на пропуск
CREATE TABLE bot_schema.requests (
    id                   VARCHAR(36) PRIMARY KEY,
    guest_name           VARCHAR(255) NOT NULL,
    visit_date           DATE NOT NULL,
    visit_time           VARCHAR(50),
    building             VARCHAR(100),
    purpose              TEXT,
    status               VARCHAR(50) DEFAULT 'pending',
    admin_comment        TEXT,
    clarification_question TEXT,
    clarification_answer   TEXT,
    initiator_id         VARCHAR(255) REFERENCES bot_schema.users(max_user_id),
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
);

-- Аудит-лог
CREATE TABLE bot_schema.audit_log (
    id           SERIAL PRIMARY KEY,
    request_id   VARCHAR(36) REFERENCES bot_schema.requests(id),
    action       VARCHAR(100),
    actor_id     VARCHAR(255),
    timestamp    TIMESTAMP DEFAULT NOW(),
    details      TEXT
);

-- Состояния FSM (для многошаговых диалогов)
CREATE TABLE bot_schema.user_states (
    user_id      VARCHAR(255) PRIMARY KEY,
    state_name   VARCHAR(100),
    data_json    TEXT,
    updated_at   TIMESTAMP DEFAULT NOW()
);

-- Администраторы (явный список ID)
CREATE TABLE bot_schema.admins (
    max_user_id  VARCHAR(255) PRIMARY KEY
);
```

## Ролевая модель

| Роль | Доступ | Идентификация |
|------|--------|---------------|
| **Инициатор** (студент/сотрудник) | Создание заявок, просмотр своих заявок, отмена до решения | По `max_user_id` из MAX |
| **Администратор** (служба безопасности) | Просмотр очереди, подтверждение/отклонение/уточнение заявок | По наличию ID в таблице `admins` |

## Принципы безопасности

1. **Разделение пользователей БД:**
   - `max_bot_admin` — для миграций (имеет право создавать таблицы)
   - `max_bot_user` — для бота (только CRUD, без DDL)

2. **Нет секретных фраз** — разграничение по ID из MAX, хранящимся в таблице `admins`

3. **Аудит каждого действия** — журнал событий по номеру заявки

4. **Дисклеймер и согласие** — при первом запуске бот показывает условия и запрашивает согласие на обработку данных

## Процессы

### Создание заявки (FSM)

1. Пользователь нажимает «Создать заявку»
2. Бот последовательно запрашивает:
   - ФИО гостя
   - Дату визита (валидация: не в прошлом)
   - Время (кнопки)
   - Корпус (кнопки)
   - Цель визита
3. Показывает сводку и кнопки «Подтвердить» / «Редактировать» / «Отменить»
4. При подтверждении создаётся заявка со статусом `pending`

### Модерация (администратор)

1. Администратор открывает меню → очередь заявок
2. Выбирает заявку → видит карточку со всеми полями
3. Может:
   - **Подтвердить** → статус `approved`, уведомление инициатору
   - **Отклонить** → выбор причины, статус `rejected`
   - **Запросить уточнение** → ввод вопроса, статус `need_clarification`

### Уточнение (инициатор)

1. Инициатор получает вопрос
2. Отвечает через кнопку «Ответить»
3. Заявка возвращается в статус `pending` и снова появляется в очереди администратора

## Запуск в production (план)

- БД — управляемый сервис (AWS RDS, DigitalOcean Managed DB)
- Бот — отдельный контейнер, миграции — при старте через `docker-entrypoint.sh`
- Образ пушится в registry (Docker Hub, GitLab Registry)
- На сервере — `docker pull` и `docker run`

## Планы на доработку

- [ ] Полная реализация FSM для создания заявки
- [ ] Обработка inline-клавиатур для модерации
- [ ] Уведомления администратора о новых заявках (webhook)
- [ ] Экспорт аудит-лога в CSV/JSON
- [ ] Unit-тесты (pytest)
- [ ] Интеграционные тесты с тестовым ботом
- [ ] Docker-сборка с минимальным образом (alpine)
- [ ] CI/CD (GitHub Actions)
- [ ] Поддержка загрузки файлов (скан пропуска)
- [ ] Статистика по заявкам (за период, по статусам)
