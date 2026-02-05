#!/bin/bash
# deploy.sh - Полное развертывание системы

set -e

echo "=== Полное развертывание Xray-Reality системы ==="

# Проверяем необходимые файлы
if [ ! -f "xray-reality/config.json" ]; then
    echo "❌ Ошибка: config.json не найден в xray-reality/"
    exit 1
fi

# Установка зависимостей
if [ -f "scripts/install_dependencies.sh" ]; then
    bash scripts/install_dependencies.sh
fi

# Останавливаем старые контейнеры
echo "Останавливаем старые контейнеры..."
docker-compose down 2>/dev/null || true

# Удаляем старые контейнеры с такими же именами
docker rm -f xray-reality 2>/dev/null || true

# Запускаем Xray
echo "Запуск Xray-Reality..."
docker-compose up -d

echo "Ожидание запуска сервисов..."
sleep 10

# Проверяем статус
echo "Проверка статуса сервисов..."
if docker ps | grep -q "xray-reality"; then
    echo "✅ Xray-Reality успешно запущен"
else
    echo "❌ Ошибка запуска Xray-Reality"
    docker logs xray-reality 2>/dev/null || true
    exit 1
fi

if docker ps | grep -q "xray-web-ui"; then
    echo "✅ Веб-интерфейс управления запущен"
else
    echo "⚠️  Веб-интерфейс управления не запущен"
    docker logs xray-web-ui 2>/dev/null || true
fi

echo "=== Развертывание завершено ==="
docker ps
