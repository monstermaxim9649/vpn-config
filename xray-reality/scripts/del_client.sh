#!/bin/bash
[ -z "$1" ] && { echo "Не указано имя пользователя"; exit 1; }

CONFIG="/app/config.json"
TMP="/tmp/config.json.tmp"

# Удаляем пользователя из конфига
jq --arg email "$1" \
  'del(.inbounds[1].settings.clients[] | select(.email == $email))' \
  "$CONFIG" > "$TMP" && cat "$TMP" > "$CONFIG"

# Перезагружаем Xray
# Перезагрузка Xray с помощью сигнала SIGHUP
echo "Перезагрузка Xray для применения изменений..."
pkill -SIGHUP xray 2>/dev/null || true

echo "Пользователь $1 удален"
