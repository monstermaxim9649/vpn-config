#!/bin/bash
set -euo pipefail

CONFIG_FILE="${CONFIG_FILE:-./xray-reality/config.json}"
SERVER_NAME="${SERVER_NAME:-mlaptev.ru}"
PUBLIC_KEY="${PUBLIC_KEY:-rXDgSWxJnp3OKBeP0evsUEzf6dJcMoxgBFspIHwcGB0}"
SNI="${SNI:-www.apple.com}"
FP="${FP:-chrome}"

PORT="${PORT:-443}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Ошибка: требуется команда '$1'." >&2
    exit 1
  fi
}

require_cmd jq
require_cmd openssl

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Ошибка: конфигурационный файл не найден: $CONFIG_FILE" >&2
  exit 1
fi

usage() {
  cat <<EOF
Использование:
  $0 add <имя_пользователя>
  $0 remove <имя_пользователя>
  $0 disable <имя_пользователя>
  $0 enable <имя_пользователя>

Переменные окружения:
  CONFIG_FILE  путь до config.json (по умолчанию ./xray-reality/config.json)
  SERVER_NAME  домен сервера для ссылки
  PUBLIC_KEY   публичный ключ Reality
  SNI          SNI для маскировки (по умолчанию www.apple.com)
  FP           fingerprint (по умолчанию chrome)

  PORT         порт подключения (по умолчанию 443)
EOF
}

if [ $# -lt 2 ]; then
  usage
  exit 1
fi

ACTION="$1"
NAME="$2"
TMP_FILE="$(mktemp)"

cleanup() {
  rm -f "$TMP_FILE"
}
trap cleanup EXIT

case "$ACTION" in
  add)
    UUID=$(cat /proc/sys/kernel/random/uuid)
    SHORT_ID=$(openssl rand -hex 3)

    jq --arg uuid "$UUID" --arg name "$NAME" --arg shortId "$SHORT_ID" \
      '.inbounds[1].settings.clients += [{"id": $uuid, "flow": "xtls-rprx-vision", "email": $name}] |
       .inbounds[1].streamSettings.realitySettings.shortIds += [$shortId]' \
      "$CONFIG_FILE" > "$TMP_FILE"
    mv "$TMP_FILE" "$CONFIG_FILE"

    docker restart xray-reality >/dev/null


    CONFIG_LINK="vless://$UUID@$SERVER_NAME:$PORT?type=tcp&security=reality&pbk=$PUBLIC_KEY&fp=$FP&sni=$SNI&sid=$SHORT_ID&spx=%2F&flow=xtls-rprx-vision#$NAME"

    echo "$CONFIG_LINK"
    ;;
  remove)
    jq --arg email "$NAME" \
      'del(.inbounds[1].settings.clients[] | select(.email == $email))' \
      "$CONFIG_FILE" > "$TMP_FILE"
    mv "$TMP_FILE" "$CONFIG_FILE"
    docker restart xray-reality >/dev/null
    echo "Пользователь $NAME удален"
    ;;
  disable)
    jq --arg email "$NAME" \
      '.inbounds[1].settings.disabledClients =
       ((.inbounds[1].settings.disabledClients // []) + [$email] | unique)' \
      "$CONFIG_FILE" > "$TMP_FILE"
    mv "$TMP_FILE" "$CONFIG_FILE"
    docker restart xray-reality >/dev/null
    echo "Пользователь $NAME отключен"
    ;;
  enable)
    jq --arg email "$NAME" \
      '.inbounds[1].settings.disabledClients =
       ((.inbounds[1].settings.disabledClients // []) | map(select(. != $email)))' \
      "$CONFIG_FILE" > "$TMP_FILE"
    mv "$TMP_FILE" "$CONFIG_FILE"
    docker restart xray-reality >/dev/null
    echo "Пользователь $NAME включен"
    ;;
  *)
    usage
    exit 1
    ;;
esac
