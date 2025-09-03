# update_bot.sh
#!/bin/bash
echo "Обновление бота..."
docker-compose restart xray-bot
echo "Готово! Логи:"
docker logs xray-telegram-bot --tail 10
