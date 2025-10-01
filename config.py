#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурация Telegram Mass Account Management Platform
"""

import os

class Config:
    """Основная конфигурация приложения"""
    
    # Flask настройки
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'telegram_mass_platform_2024_secret_key'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # База данных
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'telegram_platform.db'
    
    # Telegram API (получить на https://my.telegram.org)
    API_ID = int(os.environ.get('API_ID', '12345678'))  # Замените на ваш API ID
    API_HASH = os.environ.get('API_HASH', 'your_api_hash_here')  # Замените на ваш API Hash
    
    # Настройки сервера
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Настройки прокси
    DEFAULT_PROXY_TYPE = 'http'
    PROXY_TIMEOUT = 30
    PROXY_MAX_RETRIES = 3
    
    # Настройки рассылки
    DEFAULT_MESSAGE_DELAY = 3  # секунды
    DEFAULT_ACCOUNT_DELAY = 10  # секунд
    MAX_MESSAGES_PER_ACCOUNT = 50
    
    # Настройки безопасности
    MAX_ERRORS_PER_ACCOUNT = 10
    ACCOUNT_BLOCK_TIME = 60  # минуты
    MESSAGES_PER_HOUR_LIMIT = 100
    
    # Настройки производительности
    MAX_THREADS = 10
    ACCOUNT_POOL_SIZE = 50
    MAX_MEMORY_USAGE = 1024  # МБ
    
    # Логирование
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'telegram_platform.log'
    MAX_LOG_SIZE = 100  # МБ
    LOG_FILE_COUNT = 5
    
    # API ключи (настройте в интерфейсе)
    GOOD_PROXY_API_KEY = os.environ.get('GOOD_PROXY_API_KEY', '')
    
    # Пути к файлам
    SESSIONS_DIR = 'sessions'
    PROXIES_FILE = 'proxies.txt'
    BLACKLIST_FILE = 'blacklist.csv'
    
    @staticmethod
    def init_app(app):
        """Инициализация приложения с конфигурацией"""
        pass

class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    DATABASE_PATH = ':memory:'

# Словарь конфигураций
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}