# Xray-Reality VPN Setup

Полная система развертывания VPN сервера с Telegram ботом для управления.

## Структура проекта
├── xray-reality/ # Xray сервер

│ ├── config.json # Конфигурация Xray

│ ├── docker-compose.yml # Docker Compose для Xray

│ └── scripts/ # Скрипты управления

├── tg-bot/ # Telegram бот

│ ├── xray_bot.py # Основной код бота

│ ├── docker-compose.yml # Docker Compose для бота

│ └── Dockerfile # Образ для бота

└── scripts/ # Вспомогательные скрипты

├── deploy.sh # Скрипт развертывания

└── install_dependencies.sh # Установка зависимостей

Управление

# Статус сервисов
docker ps

# Логи Xray
docker logs xray-reality

# Логи бота
docker logs xray-telegram-bot

# Перезапуск
docker-compose -f xray-reality/docker-compose.yml restart
docker-compose -f tg-bot/docker-compose.yml restart

