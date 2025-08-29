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
