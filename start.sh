#!/bin/bash

echo ""
echo "========================================"
echo "Telegram Mass Account Management Platform"
echo "Платформа для Массового Управления Аккаунтами Telegram"
echo "========================================"
echo ""

# Проверка Python
echo "Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo "ОШИБКА: Python3 не найден! Установите Python 3.8+"
    exit 1
fi

# Проверка зависимостей
echo "Проверка зависимостей..."
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
fi

echo "Активация виртуального окружения..."
source venv/bin/activate

echo "Установка зависимостей..."
pip install -r requirements.txt

echo ""
echo "Запуск сервера..."
echo "Платформа будет доступна по адресу: http://localhost:5000"
echo "Для остановки нажмите Ctrl+C"
echo ""

python app.py