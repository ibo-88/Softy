#!/usr/bin/env python3
"""
Простая инициализация базы данных без импорта telethon
"""

import sqlite3
import os

def init_database():
    """Инициализация базы данных"""
    db_path = 'telegram_platform.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Создаем основные таблицы
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            session_file TEXT,
            api_id TEXT,
            api_hash TEXT,
            status TEXT DEFAULT 'offline',
            proxy_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proxy_id) REFERENCES proxies (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proxies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            port INTEGER,
            username TEXT,
            password TEXT,
            country TEXT,
            city TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            reason TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Новые таблицы для поиска каналов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS found_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE,
            username TEXT,
            title TEXT,
            description TEXT,
            type TEXT,
            language TEXT,
            members_count INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            join_status TEXT DEFAULT 'not_joined',
            found_by_keyword TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS join_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            account_id INTEGER,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            joined_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channel_languages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            language TEXT,
            confidence REAL,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES found_channels (channel_id)
        )
    ''')
    
    # Таблицы для кампаний
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            message TEXT,
            target_count INTEGER DEFAULT 0,
            sent_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблицы для планировщика
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            schedule_time TIMESTAMP,
            timezone TEXT DEFAULT 'UTC',
            repeat_type TEXT DEFAULT 'once',
            repeat_interval INTEGER DEFAULT 1,
            status TEXT DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
        )
    ''')
    
    # Таблицы для автоответчика
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auto_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            trigger_words TEXT,
            response_message TEXT,
            delay_seconds INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        )
    ''')
    
    # Таблицы для шаблонов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            content TEXT,
            variables TEXT,
            category TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print("✅ База данных инициализирована успешно")
    print("✅ Созданы все необходимые таблицы")

if __name__ == "__main__":
    init_database()