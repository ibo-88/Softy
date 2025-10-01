@echo off
chcp 65001 >nul
title Telegram Mass Account Management Platform

echo.
echo ========================================
echo Telegram Mass Account Management Platform
echo Платформа для Массового Управления Аккаунтами Telegram
echo ========================================
echo.

echo Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден! Установите Python 3.8+ с https://python.org
    pause
    exit /b 1
)

echo Проверка зависимостей...
if not exist "venv\" (
    echo Создание виртуального окружения...
    python -m venv venv
)

echo Активация виртуального окружения...
call venv\Scripts\activate.bat

echo Установка зависимостей...
pip install -r requirements.txt

echo.
echo Запуск сервера...
echo Платформа будет доступна по адресу: http://localhost:5000
echo Для остановки нажмите Ctrl+C
echo.

python app.py

pause