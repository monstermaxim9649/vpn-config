#!/bin/bash
set -euo pipefail

# Блокирует исходящие TLS/HTTP подключения к известным trigger-доменам,
# чтобы сервер не продлевал персональную блокировку у провайдера.

TRIGGERS=(
  "www.phpmyadmin.net"
  "phpmyadmin.net"
  "adtidy.org"
  "www.adtidy.org"
  "static.adtidy.org"
  "vimeo.com"
  "www.vimeo.com"
)

IPSET_NAME="vpn_trigger_block"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Ошибка: требуется команда '$1'" >&2
    exit 1
  fi
}

require_cmd ipset
require_cmd iptables
require_cmd getent

if ! ipset list "$IPSET_NAME" >/dev/null 2>&1; then
  ipset create "$IPSET_NAME" hash:ip family inet maxelem 65536
fi

for host in "${TRIGGERS[@]}"; do
  while IFS= read -r ip; do
    [ -n "$ip" ] || continue
    ipset add "$IPSET_NAME" "$ip" -exist
  done < <(getent ahostsv4 "$host" | awk '{print $1}' | sort -u)
done

for port in 80 443; do
  if ! iptables -C OUTPUT -p tcp --dport "$port" -m set --match-set "$IPSET_NAME" dst -j REJECT 2>/dev/null; then
    iptables -I OUTPUT -p tcp --dport "$port" -m set --match-set "$IPSET_NAME" dst -j REJECT
  fi
done

echo "Готово: блок-лист триггеров применен ($IPSET_NAME)."
echo "Проверка: iptables -S OUTPUT | grep $IPSET_NAME"
