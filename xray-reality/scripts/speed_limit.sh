#!/bin/bash

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Использование: $0 <имя_пользователя> <лимит>"
    echo "Доступные лимиты: limit_64k, limit_1m, limit_10m, limit_20m, no_limit"
    exit 1
fi

USERNAME=$1
LIMIT=$2
CONFIG_FILE="/app/config.json"
TEMP_FILE="/tmp/config.json.tmp"

echo "Устанавливаем лимит $LIMIT для пользователя $USERNAME"

# Преобразуем текстовый лимит в числовой уровень
case "$LIMIT" in
    "no_limit")
        LEVEL=0
        ;;
    "limit_64k")
        LEVEL=1
        ;;
    "limit_1m") 
        LEVEL=2
        ;;
    "limit_10m")
        LEVEL=3
        ;;
    "limit_20m")
        LEVEL=4
        ;;
    *)
        echo "Неизвестный лимит: $LIMIT"
        echo "Используйте: limit_64k, limit_1m, limit_10m, limit_20m, no_limit"
        exit 1
        ;;
esac

echo "Уровень доступа: $LEVEL"

# Обновляем уровень пользователя
jq --arg email "$USERNAME" --argjson level "$LEVEL" \
   '(.inbounds[1].settings.clients[] | select(.email == $email)).level = $level' \
   "$CONFIG_FILE" > "$TEMP_FILE" && cp "$TEMP_FILE" "$CONFIG_FILE" && rm "$TEMP_FILE"

if [ $? -ne 0 ]; then
    echo "Ошибка при обновлении конфигурации"
    exit 1
fi

echo "✅ Конфиг обновлен"

# Перезагрузка Xray
echo "Перезагружаем Xray..."
docker restart xray-reality

if [ $? -eq 0 ]; then
    echo "✅ Xray перезагружен"
else
    echo "❌ Ошибка перезагрузки Xray"
    exit 1
fi

echo "Лимит скорости для $USERNAME установлен: $LIMIT (уровень $LEVEL)"
