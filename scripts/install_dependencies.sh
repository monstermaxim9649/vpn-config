#!/bin/bash
# install_dependencies.sh

echo "Установка системных зависимостей..."

# Обновление системы
apt update
apt upgrade -y

# Установка необходимых пакетов
apt install -y \
    docker.io \
    docker-compose \
    sqlite3 \
    jq \
    curl \
    openssl \
    wget \
    git \
    ipset \
    iptables

# Добавление пользователя в группу docker
usermod -aG docker $USER

# Запуск и включение Docker
systemctl enable docker
systemctl start docker

echo "Зависимости установлены!"
