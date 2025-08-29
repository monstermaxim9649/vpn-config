#!/bin/bash
# toggle_client.sh - включает/выключает клиента

CONFIG="/opt/xray-reality/config.json"
CLIENT_EMAIL="$1"
ACTION="$2"  # "block" или "unblock"

if [ ! -f "$CONFIG" ]; then
    echo "Ошибка: файл конфигурации не найден"
    exit 1
fi

if [ -z "$CLIENT_EMAIL" ] || [ -z "$ACTION" ]; then
    echo "Использование: $0 <email> <block|unblock>"
    exit 1
fi

# Создаем временный файл
TMP_FILE=$(mktemp)

if [ "$ACTION" == "block" ]; then
    # Добавляем клиента в disabledClients (создаем массив если его нет)
    jq --arg email "$CLIENT_EMAIL" '
    if (.inbounds[1].settings.disabledClients | type == "null") then
        .inbounds[1].settings.disabledClients = [$email]
    elif (.inbounds[1].settings.disabledClients | index($email)) then
        .
    else
        .inbounds[1].settings.disabledClients += [$email]
    end' "$CONFIG" > "$TMP_FILE"
    
elif [ "$ACTION" == "unblock" ]; then
    # Удаляем клиента из disabledClients (если массив существует)
    jq --arg email "$CLIENT_EMAIL" '
    if (.inbounds[1].settings.disabledClients | type == "null") then
        .
    else
        del(.inbounds[1].settings.disabledClients[] | select(. == $email))
    end' "$CONFIG" > "$TMP_FILE"
else
    echo "Неизвестное действие: $ACTION"
    exit 1
fi

# Проверяем, что jq выполнился успешно
if [ $? -ne 0 ]; then
    echo "Ошибка при обработке JSON"
    rm -f "$TMP_FILE"
    exit 1
fi

# Применяем изменения
mv "$TMP_FILE" "$CONFIG"

# Проверяем валидность JSON
if ! jq empty "$CONFIG" 2>/dev/null; then
    echo "Ошибка: невалидный JSON после изменений"
    exit 1
fi

# Перезапускаем Xray
docker restart xray-reality >/dev/null 2>&1

echo "Успешно: клиент $CLIENT_EMAIL $ACTION"
