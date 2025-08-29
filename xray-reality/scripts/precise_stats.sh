#!/bin/bash

CONTAINER="xray-reality"
API_PORT=10085
STATS_DIR="/opt/xray-reality/stats"
STATS_DB="$STATS_DIR/stats.db"
REPORT_FILE="$STATS_DIR/report.txt"

# Создаем директорию для статистики
mkdir -p "$STATS_DIR"

# 1. Функция для безопасного создания таблицы
init_database() {
    # Проверяем существование таблицы
    if ! sqlite3 "$STATS_DB" "SELECT name FROM sqlite_master WHERE type='table' AND name='traffic_stats';" | grep -q traffic_stats; then
        echo "Создаем таблицы в базе данных..."
        sqlite3 "$STATS_DB" <<'SQL'
CREATE TABLE traffic_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER DEFAULT (strftime('%s','now')),
    user TEXT,
    direction TEXT CHECK(direction IN ('uplink', 'downlink')),
    bytes INTEGER
);
CREATE INDEX idx_user ON traffic_stats(user);
CREATE INDEX idx_timestamp ON traffic_stats(timestamp);
SQL
    fi
}

# 2. Функция для обработки данных
process_stats() {
    local json_data="$1"

    echo "$json_data" | jq -r '.stat[] | select(.name | test("user>>>.*>>>(uplink|downlink)")) |
        [.name, .value] | @tsv' | while IFS=$'\t' read -r name value; do

        user=$(echo "$name" | awk -F'>>>' '{print $2}')
        direction=$(echo "$name" | awk -F'>>>' '{print $4}')

        sqlite3 "$STATS_DB" "INSERT INTO traffic_stats (user, direction, bytes)
            VALUES ('$user', '$direction', $value);" 2>/dev/null
    done
}

# 3. Функция для генерации отчета
generate_report() {
    sqlite3 -header -column "$STATS_DB" <<'SQL' > "$REPORT_FILE"
SELECT
    user as "Пользователь",
    printf('%.2f', SUM(CASE WHEN direction = 'uplink' THEN bytes ELSE 0 END)/1048576) || ' MB' as "Отправлено",
    printf('%.2f', SUM(CASE WHEN direction = 'downlink' THEN bytes ELSE 0 END)/1048576) || ' MB' as "Получено",
    printf('%.2f', SUM(bytes)/1048576) || ' MB' as "Всего"
FROM traffic_stats
WHERE timestamp >= strftime('%s','now','-1 day')
GROUP BY user
ORDER BY SUM(bytes) DESC;
SQL
}

# Основной поток выполнения
init_database

# Получаем данные через API
echo "Получение данных из API..."
STATS_JSON=$(docker exec "$CONTAINER" sh -c \
    "/usr/bin/xray api statsquery --server=127.0.0.1:$API_PORT -pattern '' -reset" 2>/dev/null || echo '{"stat":[]}')

# Обрабатываем статистику
process_stats "$STATS_JSON"

# Проверяем что данные добавились
echo "Записей в базе: $(sqlite3 "$STATS_DB" "SELECT COUNT(*) FROM traffic_stats;")"

# Генерируем отчет
generate_report

# Выводим результат
echo "Точная статистика трафика (последние 24 часа):"
echo "-------------------------------------------"
cat "$REPORT_FILE"
