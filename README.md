# Xray-Reality VPN Setup

Полная система развертывания VPN сервера с веб-интерфейсом и локальными CLI-скриптами.

## Структура проекта
├── xray-reality/ # Xray сервер
│ ├── config.json # Конфигурация Xray
│ └── logs/ # Логи
├── scripts/ # Вспомогательные скрипты
│ ├── deploy.sh # Скрипт развертывания
│ ├── install_dependencies.sh # Установка зависимостей
│ └── manage_clients.sh # CLI для управления пользователями
└── web-ui/ # Веб-интерфейс управления
    ├── app.py
    ├── templates/
    └── static/

## Управление

# Статус сервисов
```
docker ps
```

# Логи Xray
```
docker logs xray-reality
```

# Логи веб-интерфейса
```
docker logs xray-web-ui
```

# Перезапуск
```
docker-compose restart
```

## Веб-интерфейс управления

1. Заполните переменные окружения для сервиса `xray-web-ui` в `docker-compose.yml`:
   - `SERVER_NAME`, `PUBLIC_KEY` (для генерации ссылок)
   - `SNI`, `PORT` можно не задавать: по умолчанию используются значения из `xray-reality/config.json`
   - `FP` (fingerprint, по умолчанию `chrome`)
   - `UI_USERNAME`, `UI_PASSWORD`, `SECRET_KEY` (доступ к панели)
2. Запустите сервисы:
```
docker-compose up -d
```
3. Откройте панель: `http://<IP_сервера>:8080`.

Панель позволяет добавлять/удалять/включать/отключать пользователей без смены ключей и автоматически перезапускает контейнер Xray. При добавлении клиента UI использует существующий `shortId` из конфигурации и не меняет список, если он уже задан. Для дополнительной маскировки можно менять `dest` и `serverNames` в `xray-reality/config.json`, избегая известных триггеров (например, `vimeo.com`, `phpmyadmin.net`, `*.adtidy.org`), а в ссылках использовать другой `FP`.


## Дополнительно: снижение риска продления блокировки

Если блокировка уже активна, важно не допускать исходящих обращений с сервера к известным trigger-доменам (например `phpmyadmin.net`, `*.adtidy.org`, `vimeo.com`) на 80/443.

Применить защитный блок-лист:
```
sudo ./scripts/apply_trigger_blocks.sh
```

Проверить правила:
```
iptables -S OUTPUT | grep vpn_trigger_block
ipset list vpn_trigger_block
```

## Управление пользователями (CLI, без Telegram)

# Добавить пользователя и получить ссылку
```
SERVER_NAME="your-domain.com" PUBLIC_KEY="your-public-key" ./scripts/manage_clients.sh add <имя>
```

# Удалить пользователя
```
./scripts/manage_clients.sh remove <имя>
```

# Отключить пользователя
```
./scripts/manage_clients.sh disable <имя>
```

# Включить пользователя
```
./scripts/manage_clients.sh enable <имя>
```
