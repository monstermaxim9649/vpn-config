#!/bin/bash

BOT_SCRIPT="/opt/tg_bot/xray_bot.py"
SERVICE_NAME="xray_bot.service"
LOG_FILE="/var/log/xray_bot.log"
LOCK_FILE="/tmp/xray_bot.lock"

# Проверяем lock-файл
if [ -f "$LOCK_FILE" ]; then
    echo "$(date) - Обнаружен lock-файл, предыдущий запуск еще выполняется" >> $LOG_FILE
    exit 0
fi

# Создаем lock-файл
touch $LOCK_FILE

# Проверяем, работает ли бот
if ! pgrep -f "python3 $BOT_SCRIPT" > /dev/null; then
    echo "$(date) - Бот не работает, перезапускаем..." >> $LOG_FILE
    systemctl restart $SERVICE_NAME
else
    echo "$(date) - Бот работает нормально" >> $LOG_FILE
fi

# Удаляем lock-файл
rm -f $LOCK_FILE
