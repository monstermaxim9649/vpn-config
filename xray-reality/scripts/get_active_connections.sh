#!/bin/bash
# get_active_connections.sh - получаем активных пользователей через API

API_URL="http://xray-reality:10085/stats"

# Пытаемся получить данные через API
response=$(curl -s -f "$API_URL" 2>/dev/null)

    if [ -f "/var/log/xray/access.log" ]; then
        grep "accepted" "/var/log/xray/access.log" 2>/dev/null | \
        tail -n 50 | grep -o 'email: [^ ]*' | cut -d' ' -f2 | sort -u
    else
        echo "Нет активных подключений"
    fi
