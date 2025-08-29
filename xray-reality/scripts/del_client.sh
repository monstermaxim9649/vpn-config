#!/bin/bash
[ -z "$1" ] && { echo "Не указано имя пользователя"; exit 1; }

CONFIG="/opt/xray-reality/config.json"
TMP="/tmp/config.json.tmp"

# Удаляем пользователя из конфига
jq --arg email "$1" \
  'del(.inbounds[1].settings.clients[] | select(.email == $email))' \
  "$CONFIG" > "$TMP" && mv "$TMP" "$CONFIG"

# Перезагружаем Xray
docker restart xray-reality

echo "Пользователь $1 удален"
