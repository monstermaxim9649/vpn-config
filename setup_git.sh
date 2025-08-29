#!/bin/bash
# setup_git.sh - Подготовка и заливка в Git репозиторий

set -e

echo "=== Подготовка репозитория ==="

# Создаем временную директорию для репозитория
REPO_DIR="/opt/vpn-config"
mkdir -p $REPO_DIR
cd $REPO_DIR

# Инициализируем Git репозиторий
git init
git config user.name "monstermaxim9649"
git config user.email "monstermaxim9649@gmail.com"

# Создаем структуру директорий
mkdir -p xray-reality/scripts
mkdir -p xray-reality/stats
mkdir -p tg-bot
mkdir -p scripts

# Копируем файлы Xray-reality
echo "Копируем Xray-reality файлы..."
cp /opt/xray-reality/config.json xray-reality/
cp /opt/xray-reality/scripts/*.sh xray-reality/scripts/

# Копируем Telegram bot файлы
echo "Копируем Telegram bot файлы..."
cp /opt/tg_bot/* tg-bot/

# Создаем основные файлы конфигурации
echo "Создаем Docker Compose и вспомогательные файлы..."

# Docker Compose для Xray
cat > xray-reality/docker-compose.yml << 'EOF'
version: '3.8'

services:
  xray-reality:
    image: teddysun/xray:latest
    container_name: xray-reality
    restart: unless-stopped
    ports:
      - "443:443"
    volumes:
      - ./config.json:/etc/xray/config.json
      - ./logs:/var/log/xray
      - ./stats:/opt/xray/stats
    networks:
      - xray-network
    healthcheck:
      test: ["CMD", "wget", "--spider", "--quiet", "http://127.0.0.1:10085/stats"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  xray-network:
    driver: bridge
EOF

# Docker Compose для Telegram bot
cat > tg-bot/docker-compose.yml << 'EOF'
version: '3.8'

services:
  xray-bot:
    build: .
    container_name: xray-telegram-bot
    restart: unless-stopped
    volumes:
      - ./xray_bot.py:/app/xray_bot.py
      - ../xray-reality/scripts:/app/scripts
      - ../xray-reality/stats:/app/stats
      - ../xray-reality/config.json:/app/config.json
    depends_on:
      - xray-reality
    environment:
      - TZ=Europe/Moscow
    networks:
      - xray-network

networks:
  xray-network:
    external: true
    name: xray-reality_xray-network
EOF

# Dockerfile для бота
cat > tg-bot/Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    sqlite3 \
    jq \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "xray_bot.py"]
EOF

# requirements.txt для бота
cat > tg-bot/requirements.txt << 'EOF'
python-telegram-bot==13.7
requests==2.28.0
pyyaml==6.0
EOF

# Скрипт установки зависимостей
cat > scripts/install_dependencies.sh << 'EOF'
#!/bin/bash
# install_dependencies.sh

echo "Установка системных зависимостей..."

# Обновление системы
apt update
apt upgrade -y

# Установка необходимых пакетов
apt install -y \
    docker.io \
    docker-compose \
    sqlite3 \
    jq \
    curl \
    wget \
    git

# Добавление пользователя в группу docker
usermod -aG docker $USER

# Запуск и включение Docker
systemctl enable docker
systemctl start docker

echo "Зависимости установлены!"
EOF

# Скрипт деплоя
cat > scripts/deploy.sh << 'EOF'
#!/bin/bash
# deploy.sh - Полное развертывание системы

set -e

echo "=== Полное развертывание Xray-Reality системы ==="

# Установка зависимостей
if [ -f "install_dependencies.sh" ]; then
    bash install_dependencies.sh
fi

# Развертывание Xray
echo "Развертывание Xray-Reality..."
cd xray-reality

# Останавливаем старый контейнер если существует
if docker ps -a | grep -q "xray-reality"; then
    echo "Останавливаем старый контейнер..."
    docker stop xray-reality || true
    docker rm xray-reality || true
fi

# Запускаем новый контейнер
docker-compose up -d

echo "Ожидание запуска Xray..."
sleep 5

# Проверяем статус
if docker ps | grep -q "xray-reality"; then
    echo "✅ Xray-Reality успешно запущен"
else
    echo "❌ Ошибка запуска Xray-Reality"
    docker logs xray-reality
    exit 1
fi

# Развертывание Telegram bot (если нужно)
if [ -d "../tg-bot" ]; then
    echo "Развертывание Telegram bot..."
    cd ../tg-bot
    
    # Собираем и запускаем бота
    docker-compose up -d --build
    
    echo "Ожидание запуска бота..."
    sleep 3
    
    if docker ps | grep -q "xray-telegram-bot"; then
        echo "✅ Telegram bot успешно запущен"
    else
        echo "⚠️  Возможна ошибка запуска бота"
        docker logs xray-telegram-bot
    fi
fi

echo "=== Развертывание завершено ==="
echo "Проверьте логи:"
echo "Xray: docker logs xray-reality"
echo "Bot:  docker logs xray-telegram-bot"
EOF

# .gitignore
cat > .gitignore << 'EOF'
# Logs
*.log
logs/
access.log
stats.log
traffic.log

# Database
*.db
*.sqlite
*.sqlite3

# Sensitive data
*.key
*.pem
*.crt
.env
secrets/

# Temporary files
*.tmp
*.temp
.tmp/
.temp/

# Docker
Dockerfile
docker-compose.override.yml

# System
.DS_Store
Thumbs.db

# Backups
*.bak
*.backup
*.tar
*.gz
EOF

# README.md
cat > README.md << 'EOF'
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

EOF
