#!/bin/bash
# speed_limit.sh - управление ограничением скорости

CONFIG="/app/config.json"
CLIENT_EMAIL="$1"
ACTION="$2"

if [ ! -f "$CONFIG" ]; then
    echo "Ошибка: файл конфигурации не найден"
    exit 1
fi

if [ -z "$CLIENT_EMAIL" ] || [ -z "$ACTION" ]; then
    echo "Использование: $0 <email> <limit_64k|limit_1m|limit_10m|limit_20m|unlimit>"
    exit 1
fi

# Создаем временный файл
TMP_FILE=$(mktemp)

case "$ACTION" in
    "limit_64k")
        LEVEL=1
        SPEED_TEXT="64 KB/s"
        ;;
    "limit_1m")
        LEVEL=2
        SPEED_TEXT="1 MB/s"
        ;;
    "limit_10m")
        LEVEL=3
        SPEED_TEXT="10 MB/s"
        ;;
    "limit_20m")
        LEVEL=4
        SPEED_TEXT="20 MB/s"
        ;;
    "unlimit")
        LEVEL=0
        SPEED_TEXT="без ограничений"
        ;;
    *)
        echo "Неизвестное действие: $ACTION"
        exit 1
        ;;
esac

# Проверяем существование пользователя
if ! jq -e --arg email "$CLIENT_EMAIL" '.inbounds[1].settings.clients[] | select(.email == $email)' "$CONFIG" > /dev/null; then
    echo "Ошибка: пользователь $CLIENT_EMAIL не найден"
    exit 1
fi

# Обновляем уровень пользователя
jq --arg email "$CLIENT_EMAIL" --argjson level "$LEVEL" \
'(.inbounds[1].settings.clients[] | select(.email == $email)).level = $level' \
"$CONFIG" > "$TMP_FILE"

# Проверяем успешность выполнения
if [ $? -ne 0 ]; then
    echo "Ошибка при обработке JSON"
    rm -f "$TMP_FILE"
    exit 1
fi

# Проверяем валидность JSON
if ! jq empty "$TMP_FILE" 2>/dev/null; then
    echo "Ошибка: невалидный JSON после изменений"
    rm -f "$TMP_FILE"
    exit 1
fi

# Применяем изменения
mv "$TMP_FILE" "$CONFIG"

# Перезапускаем Xray
docker restart xray-reality >/dev/null 2>&1

echo "Успешно: клиенту $CLIENT_EMAIL установлена скорость $SPEED_TEXT"
