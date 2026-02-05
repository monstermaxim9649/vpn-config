#!/bin/bash

# Проверка наличия аргумента (имя пользователя)
if [ -z "$1" ]; then
    echo "Использование: $0 <имя_пользователя>"
    exit 1
fi

NAME=$1
CONFIG_FILE="/app/config.json"
TEMP_FILE="/tmp/config.json.tmp"

# Проверяем существование конфигурационного файла
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Ошибка: Конфигурационный файл $CONFIG_FILE не найден"
    exit 1
fi

# Генерируем uuid для клиента
UUID=$(cat /proc/sys/kernel/random/uuid)

# Генерируем короткий ID (6 символов)
SHORT_ID=$(openssl rand -hex 3)

# Добавляем клиента во второй inbound (порт 443)
jq --arg uuid "$UUID" --arg name "$NAME" --arg shortId "$SHORT_ID" \
   '.inbounds[1].settings.clients += [{"id": $uuid, "flow": "xtls-rprx-vision", "email": $name}] |
    .inbounds[1].streamSettings.realitySettings.shortIds += [$shortId]' \
   "$CONFIG_FILE" > "$TEMP_FILE" && cp "$TEMP_FILE" "$CONFIG_FILE" && rm "$TEMP_FILE"

if [ $? -ne 0 ]; then
    echo "Ошибка при обновлении конфигурации"
    exit 1
fi

#echo "✅ Пользователь $NAME добавлен в конфиг"

# ПЕРЕЗАГРУЗКА XRAY - КРИТИЧЕСКИ ВАЖНО
#echo "Перезагружаем Xray..."
docker restart xray-reality

#if [ $? -eq 0 ]; then
#    echo "✅ Xray перезагружен успешно"
#else
#    echo "❌ Ошибка перезагрузки Xray"
#    exit 1
#fi

# Получаем параметры сервера из конфига
SERVER_NAME="mlaptev.ru"  # Ваш домен
PUBLIC_KEY="rXDgSWxJnp3OKBeP0evsUEzf6dJcMoxgBFspIHwcGB0"  # Ваш публичный ключ
SNI="www.cloudflare.com"  # SNI для маскировки
PORT=443

# Формируем ссылку для подключения в точном формате
CONFIG_LINK="vless://$UUID@$SERVER_NAME:$PORT?type=tcp&security=reality&pbk=$PUBLIC_KEY&fp=chrome&sni=$SNI&sid=$SHORT_ID&spx=%2F&flow=xtls-rprx-vision#$NAME"

echo "$CONFIG_LINK"
