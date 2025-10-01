#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Mass Account Management Platform
Платформа для Массового Управления Аккаунтами Telegram
"""

import os
import sys
import json
import sqlite3
import threading
import asyncio
import time
import random
import logging
import shutil
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserBannedError, ChatWriteForbiddenError
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import InputPeerChannel, InputPeerChat, InputPeerUser
import requests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_platform.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'telegram_mass_platform_2024'

# Глобальные переменные
accounts_pool = []
proxy_pool = []
blacklist = set()
active_tasks = {}
task_logs = {}

class DatabaseManager:
    def __init__(self, db_path='telegram_platform.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица аккаунтов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                status TEXT DEFAULT 'offline',
                proxy_id INTEGER,
                geo_country TEXT,
                session_file TEXT,
                api_id INTEGER,
                api_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_check TIMESTAMP,
                FOREIGN KEY (proxy_id) REFERENCES proxies (id)
            )
        ''')
        
        # Таблица прокси
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                port INTEGER,
                username TEXT,
                password TEXT,
                country TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица blacklist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
                reason TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица парсинга
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parsed_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                user_id TEXT,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                bio TEXT,
                is_bot BOOLEAN DEFAULT 0,
                is_verified BOOLEAN DEFAULT 0,
                is_premium BOOLEAN DEFAULT 0,
                last_seen INTEGER,
                common_chats_count INTEGER DEFAULT 0,
                parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица кампаний
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                message TEXT,
                target_count INTEGER,
                sent_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # Таблица задач парсинга
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parsing_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                source_type TEXT,
                source_data TEXT,
                status TEXT DEFAULT 'pending',
                results_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # Таблица рассылок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                message TEXT,
                media_path TEXT,
                target_count INTEGER,
                sent_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # Таблица логов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                action TEXT,
                target TEXT,
                status TEXT,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")

class ProxyManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.good_proxy_api_key = None
    
    def load_proxies_from_file(self, file_path):
        """Загрузка прокси из файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            loaded_count = 0
            for line in lines:
                line = line.strip()
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        ip = parts[0]
                        port = int(parts[1])
                        username = parts[2] if len(parts) > 2 else ''
                        password = parts[3] if len(parts) > 3 else ''
                        
                        cursor.execute('''
                            INSERT OR IGNORE INTO proxies (ip, port, username, password)
                            VALUES (?, ?, ?, ?)
                        ''', (ip, port, username, password))
                        loaded_count += 1
            
            conn.commit()
            conn.close()
            logger.info(f"Загружено {loaded_count} прокси из файла")
            return loaded_count
        except Exception as e:
            logger.error(f"Ошибка загрузки прокси из файла: {e}")
            return 0
    
    def get_proxies_from_api(self, api_key):
        """Получение прокси через API good proxy"""
        try:
            # Здесь должен быть реальный API запрос к good proxy
            # Для демонстрации возвращаем тестовые данные
            self.good_proxy_api_key = api_key
            
            # Имитация API запроса
            test_proxies = [
                {"ip": "192.168.1.1", "port": 8080, "username": "user1", "password": "pass1", "country": "DE"},
                {"ip": "192.168.1.2", "port": 8080, "username": "user2", "password": "pass2", "country": "US"},
                {"ip": "192.168.1.3", "port": 8080, "username": "user3", "password": "pass3", "country": "RU"},
            ]
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            for proxy in test_proxies:
                cursor.execute('''
                    INSERT OR IGNORE INTO proxies (ip, port, username, password, country)
                    VALUES (?, ?, ?, ?, ?)
                ''', (proxy["ip"], proxy["port"], proxy["username"], 
                      proxy["password"], proxy["country"]))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Получено {len(test_proxies)} прокси из API good proxy")
            return len(test_proxies)
        except Exception as e:
            logger.error(f"Ошибка получения прокси из API: {e}")
            return 0

class AccountManager:
    def __init__(self, db_manager, proxy_manager):
        self.db = db_manager
        self.proxy_manager = proxy_manager
        self.accounts = {}
    
    def load_sessions_from_folder(self, folder_path):
        """Массовая загрузка сессий из папки"""
        try:
            session_files = []
            for file in os.listdir(folder_path):
                if file.endswith('.session'):
                    session_files.append(os.path.join(folder_path, file))
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            loaded_count = 0
            for session_file in session_files:
                try:
                    # Извлекаем номер телефона из имени файла
                    phone = os.path.basename(session_file).replace('.session', '')
                    
                    # Извлекаем API ключи из сессии
                    api_id, api_hash = extract_api_from_session(session_file)
                    
                    # Пытаемся получить информацию об аккаунте
                    try:
                        client = TelegramClient(session_file, api_id, api_hash)
                        with client:
                            me = client.get_me()
                            username = me.username or ''
                            first_name = me.first_name or ''
                            last_name = me.last_name or ''
                            status = 'online'
                    except Exception as e:
                        logger.warning(f"Не удалось подключиться к аккаунту {phone}: {e}")
                        username = ''
                        first_name = ''
                        last_name = ''
                        status = 'offline'
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO accounts (phone, username, first_name, last_name, status, session_file, api_id, api_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (phone, username, first_name, last_name, status, session_file, api_id, api_hash))
                    loaded_count += 1
                    
                    logger.info(f"Загружен аккаунт: {phone} (@{username}) - {first_name} {last_name}")
                    
                except Exception as e:
                    logger.error(f"Ошибка загрузки сессии {session_file}: {e}")
            
            conn.commit()
            conn.close()
            
            logger.info(f"Загружено {loaded_count} сессий из папки")
            return loaded_count
        except Exception as e:
            logger.error(f"Ошибка загрузки сессий: {e}")
            return 0
    
    def assign_geo_proxies(self, country):
        """Назначение прокси по геолокации"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Получаем прокси из указанной страны
            cursor.execute('SELECT id FROM proxies WHERE country = ? AND is_active = 1', (country,))
            proxy_ids = [row[0] for row in cursor.fetchall()]
            
            if not proxy_ids:
                logger.warning(f"Не найдены прокси для страны {country}")
                return 0
            
            # Получаем аккаунты без назначенных прокси
            cursor.execute('SELECT id FROM accounts WHERE proxy_id IS NULL')
            account_ids = [row[0] for row in cursor.fetchall()]
            
            assigned_count = 0
            for i, account_id in enumerate(account_ids):
                proxy_id = proxy_ids[i % len(proxy_ids)]
                cursor.execute('''
                    UPDATE accounts SET proxy_id = ?, geo_country = ?
                    WHERE id = ?
                ''', (proxy_id, country, account_id))
                assigned_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"Назначено {assigned_count} прокси для страны {country}")
            return assigned_count
        except Exception as e:
            logger.error(f"Ошибка назначения гео-прокси: {e}")
            return 0
    
    def mass_check_accounts(self):
        """Массовая проверка аккаунтов (ТП)"""
        def check_account(account_id, session_file, api_id, api_hash, proxy_data):
            try:
                # Создаем клиент с прокси
                client = TelegramClient(session_file, api_id, api_hash)
                
                if proxy_data:
                    proxy = {
                        'proxy_type': 'http',
                        'addr': proxy_data['ip'],
                        'port': proxy_data['port'],
                        'username': proxy_data['username'],
                        'password': proxy_data['password']
                    }
                    client.set_proxy(proxy)
                
                # Проверяем подключение
                with client:
                    me = client.get_me()
                    status = 'online'
                    username = me.username or ''
                    first_name = me.first_name or ''
                    last_name = me.last_name or ''
                
                # Обновляем статус в БД
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE accounts SET status = ?, username = ?, first_name = ?, last_name = ?, last_check = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, username, first_name, last_name, account_id))
                conn.commit()
                conn.close()
                
                logger.info(f"Аккаунт {account_id} (@{username}): ТП пройдена, статус 🟢 Онлайн")
                
            except Exception as e:
                # Обновляем статус на ошибку
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE accounts SET status = 'banned', last_check = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (account_id,))
                conn.commit()
                conn.close()
                
                logger.error(f"Аккаунт {account_id}: Ошибка проверки - {e}")
        
        # Запускаем проверку в отдельных потоках
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, a.session_file, a.api_id, a.api_hash, p.ip, p.port, p.username, p.password
            FROM accounts a
            LEFT JOIN proxies p ON a.proxy_id = p.id
            WHERE a.status != 'banned' AND a.api_id IS NOT NULL
        ''')
        
        accounts_to_check = cursor.fetchall()
        conn.close()
        
        threads = []
        for account_data in accounts_to_check:
            account_id, session_file, api_id, api_hash, ip, port, username, password = account_data
            proxy_data = None
            if ip:
                proxy_data = {'ip': ip, 'port': port, 'username': username, 'password': password}
            
            thread = threading.Thread(target=check_account, args=(account_id, session_file, api_id, api_hash, proxy_data))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        logger.info(f"Запущена проверка {len(accounts_to_check)} аккаунтов")
        return len(accounts_to_check)

class AccountRegistrationManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.sms_services = {
            'sms-activate': 'https://api.sms-activate.org/stubs/handler_api.php',
            '5sim': 'https://5sim.net/v1',
            'sms-man': 'https://sms-man.ru/api'
        }
    
    def register_account(self, phone_number, api_id, api_hash, sms_service='sms-activate'):
        """Регистрация нового аккаунта Telegram"""
        try:
            # Создаем клиент для регистрации
            client = TelegramClient(f'sessions/{phone_number}', api_id, api_hash)
            
            with client:
                # Отправляем код подтверждения
                client.send_code_request(phone_number)
                logger.info(f"Код отправлен на номер {phone_number}")
                
                # Получаем код через SMS сервис
                code = self.get_sms_code(phone_number, sms_service)
                
                if not code:
                    logger.error(f"Не удалось получить SMS код для {phone_number}")
                    return False
                
                # Подтверждаем код
                client.sign_in(phone_number, code)
                
                # Получаем информацию об аккаунте
                me = client.get_me()
                
                # Сохраняем в базу данных
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO accounts (phone, username, first_name, last_name, status, session_file, api_id, api_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (phone_number, me.username or '', me.first_name or '', me.last_name or '', 'online', 
                      f'sessions/{phone_number}.session', api_id, api_hash))
                conn.commit()
                conn.close()
                
                logger.info(f"Аккаунт {phone_number} успешно зарегистрирован")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка регистрации аккаунта {phone_number}: {e}")
            return False
    
    def get_sms_code(self, phone_number, sms_service):
        """Получение SMS кода через сервис"""
        try:
            if sms_service == 'sms-activate':
                # Здесь должен быть реальный API запрос к sms-activate
                # Для демонстрации возвращаем случайный код
                import random
                return str(random.randint(100000, 999999))
            
            # Добавить другие SMS сервисы
            return None
        except Exception as e:
            logger.error(f"Ошибка получения SMS кода: {e}")
            return None
    
    def mass_registration(self, phone_numbers, api_id, api_hash, sms_service='sms-activate'):
        """Массовая регистрация аккаунтов"""
        success_count = 0
        failed_count = 0
        
        for phone in phone_numbers:
            if self.register_account(phone, api_id, api_hash, sms_service):
                success_count += 1
            else:
                failed_count += 1
            
            # Задержка между регистрациями
            time.sleep(random.randint(30, 60))
        
        logger.info(f"Массовая регистрация завершена: {success_count} успешно, {failed_count} ошибок")
        return {'success': success_count, 'failed': failed_count}

class AccountManagementManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def update_account_profile(self, account_id, profile_data):
        """Обновление профиля аккаунта"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT session_file, api_id, api_hash FROM accounts WHERE id = ?', (account_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            session_file, api_id, api_hash = result
            
            # Обновляем профиль через Telegram API
            client = TelegramClient(session_file, api_id, api_hash)
            
            with client:
                # Обновляем имя
                if profile_data.get('first_name') or profile_data.get('last_name'):
                    client(UpdateProfileRequest(
                        first_name=profile_data.get('first_name', ''),
                        last_name=profile_data.get('last_name', '')
                    ))
                
                # Обновляем описание
                if profile_data.get('about'):
                    client(UpdateProfileRequest(about=profile_data.get('about')))
                
                # Обновляем аватар
                if profile_data.get('avatar_path'):
                    client(UploadProfilePhotoRequest(
                        file=client.upload_file(profile_data['avatar_path'])
                    ))
            
            # Обновляем в базе данных
            cursor.execute('''
                UPDATE accounts SET first_name = ?, last_name = ?, username = ?
                WHERE id = ?
            ''', (profile_data.get('first_name', ''), profile_data.get('last_name', ''), 
                  profile_data.get('username', ''), account_id))
            conn.commit()
            conn.close()
            
            logger.info(f"Профиль аккаунта {account_id} обновлен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления профиля аккаунта {account_id}: {e}")
            return False
    
    def mass_update_profiles(self, account_ids, profile_data):
        """Массовое обновление профилей"""
        success_count = 0
        
        for account_id in account_ids:
            if self.update_account_profile(account_id, profile_data):
                success_count += 1
            
            # Задержка между обновлениями
            time.sleep(random.randint(5, 15))
        
        logger.info(f"Массовое обновление профилей: {success_count}/{len(account_ids)} успешно")
        return success_count

class InvitationManager:
    def __init__(self, db_manager, account_manager):
        self.db = db_manager
        self.account_manager = account_manager
    
    def send_invitations(self, target_usernames, chat_link, message="Приглашаю вас в наш чат!"):
        """Отправка массовых приглашений в чат/канал"""
        try:
            # Получаем активные аккаунты
            active_accounts = self.get_active_accounts()
            
            if not active_accounts:
                logger.error("Нет активных аккаунтов для отправки приглашений")
                return False
            
            success_count = 0
            error_count = 0
            
            for username in target_usernames:
                # Выбираем случайный аккаунт
                account = random.choice(active_accounts)
                
                try:
                    client = TelegramClient(account['session_file'], account['api_id'], account['api_hash'])
                    
                    # Настраиваем прокси если есть
                    if account['proxy']:
                        proxy = {
                            'proxy_type': 'http',
                            'addr': account['proxy']['ip'],
                            'port': account['proxy']['port'],
                            'username': account['proxy']['username'],
                            'password': account['proxy']['password']
                        }
                        client.set_proxy(proxy)
                    
                    with client:
                        # Отправляем сообщение с приглашением
                        client.send_message(username, f"{message}\n\n{chat_link}")
                        success_count += 1
                        logger.info(f"Приглашение отправлено {username} через аккаунт {account['id']}")
                
                except Exception as e:
                    error_count += 1
                    logger.error(f"Ошибка отправки приглашения {username}: {e}")
                
                # Задержка между приглашениями
                time.sleep(random.randint(10, 30))
            
            logger.info(f"Отправка приглашений завершена: {success_count} успешно, {error_count} ошибок")
            return {'success': success_count, 'errors': error_count}
            
        except Exception as e:
            logger.error(f"Ошибка отправки приглашений: {e}")
            return False
    
    def get_active_accounts(self):
        """Получение активных аккаунтов"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.id, a.session_file, a.api_id, a.api_hash, p.ip, p.port, p.username, p.password
                FROM accounts a
                LEFT JOIN proxies p ON a.proxy_id = p.id
                WHERE a.status = 'online' AND a.api_id IS NOT NULL
            ''')
            
            accounts = []
            for row in cursor.fetchall():
                account = {
                    'id': row[0],
                    'session_file': row[1],
                    'api_id': row[2],
                    'api_hash': row[3],
                    'proxy': None
                }
                
                if row[4]:
                    account['proxy'] = {
                        'ip': row[4], 'port': row[5],
                        'username': row[6], 'password': row[7]
                    }
                
                accounts.append(account)
            
            conn.close()
            return accounts
        except Exception as e:
            logger.error(f"Ошибка получения активных аккаунтов: {e}")
            return []

class SubscriptionManager:
    def __init__(self, db_manager, account_manager):
        self.db = db_manager
        self.account_manager = account_manager
    
    def mass_subscribe(self, target_channels, account_ids=None):
        """Массовая подписка на каналы"""
        try:
            if not account_ids:
                # Получаем все активные аккаунты
                active_accounts = self.get_active_accounts()
                account_ids = [acc['id'] for acc in active_accounts]
            
            success_count = 0
            error_count = 0
            
            for account_id in account_ids:
                try:
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT session_file, api_id, api_hash FROM accounts WHERE id = ?', (account_id,))
                    result = cursor.fetchone()
                    conn.close()
                    
                    if not result:
                        continue
                    
                    session_file, api_id, api_hash = result
                    client = TelegramClient(session_file, api_id, api_hash)
                    
                    with client:
                        for channel in target_channels:
                            try:
                                # Подписываемся на канал
                                client(JoinChannelRequest(channel))
                                success_count += 1
                                logger.info(f"Аккаунт {account_id} подписался на {channel}")
                                
                                # Задержка между подписками
                                time.sleep(random.randint(5, 15))
                                
                            except Exception as e:
                                error_count += 1
                                logger.error(f"Ошибка подписки на {channel}: {e}")
                
                except Exception as e:
                    error_count += 1
                    logger.error(f"Ошибка работы с аккаунтом {account_id}: {e}")
                
                # Задержка между аккаунтами
                time.sleep(random.randint(30, 60))
            
            logger.info(f"Массовая подписка завершена: {success_count} успешно, {error_count} ошибок")
            return {'success': success_count, 'errors': error_count}
            
        except Exception as e:
            logger.error(f"Ошибка массовой подписки: {e}")
            return False
    
    def get_active_accounts(self):
        """Получение активных аккаунтов"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.id, a.session_file, a.api_id, a.api_hash, p.ip, p.port, p.username, p.password
                FROM accounts a
                LEFT JOIN proxies p ON a.proxy_id = p.id
                WHERE a.status = 'online' AND a.api_id IS NOT NULL
            ''')
            
            accounts = []
            for row in cursor.fetchall():
                account = {
                    'id': row[0],
                    'session_file': row[1],
                    'api_id': row[2],
                    'api_hash': row[3],
                    'proxy': None
                }
                
                if row[4]:
                    account['proxy'] = {
                        'ip': row[4], 'port': row[5],
                        'username': row[6], 'password': row[7]
                    }
                
                accounts.append(account)
            
            conn.close()
            return accounts
        except Exception as e:
            logger.error(f"Ошибка получения активных аккаунтов: {e}")
            return []

class SessionCloningManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def clone_session(self, original_session_path, new_phone_number, api_id, api_hash):
        """Клонирование сессии для защиты от недобросовестных продавцов"""
        try:
            # Копируем файл сессии
            new_session_path = f'sessions/{new_phone_number}.session'
            shutil.copy2(original_session_path, new_session_path)
            
            # Создаем новый клиент с клонированной сессией
            client = TelegramClient(new_session_path, api_id, api_hash)
            
            with client:
                # Проверяем работоспособность клонированной сессии
                me = client.get_me()
                
                # Сохраняем в базу данных
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO accounts (phone, username, first_name, last_name, status, session_file, api_id, api_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (new_phone_number, me.username or '', me.first_name or '', me.last_name or '', 'online', 
                      new_session_path, api_id, api_hash))
                conn.commit()
                conn.close()
                
                logger.info(f"Сессия клонирована для номера {new_phone_number}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка клонирования сессии: {e}")
            return False
    
    def mass_clone_sessions(self, original_session_path, phone_numbers, api_id, api_hash):
        """Массовое клонирование сессий"""
        success_count = 0
        
        for phone in phone_numbers:
            if self.clone_session(original_session_path, phone, api_id, api_hash):
                success_count += 1
            
            # Задержка между клонированием
            time.sleep(random.randint(10, 20))
        
        logger.info(f"Массовое клонирование завершено: {success_count}/{len(phone_numbers)} успешно")
        return success_count

class ParsingManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.active_tasks = {}
    
    def parse_channel(self, channel_link, max_users=1000):
        """Парсинг участников канала"""
        try:
            # Получаем активный аккаунт
            active_account = self.get_active_account()
            if not active_account:
                logger.error("Нет активных аккаунтов для парсинга")
                return False
            
            client = TelegramClient(active_account['session_file'], active_account['api_id'], active_account['api_hash'])
            
            # Настраиваем прокси если есть
            if active_account['proxy']:
                proxy = {
                    'proxy_type': 'http',
                    'addr': active_account['proxy']['ip'],
                    'port': active_account['proxy']['port'],
                    'username': active_account['proxy']['username'],
                    'password': active_account['proxy']['password']
                }
                client.set_proxy(proxy)
            
            with client:
                # Получаем информацию о канале
                entity = client.get_entity(channel_link)
                
                # Парсим участников
                participants = client.get_participants(entity, limit=max_users)
                
                # Сохраняем в базу данных
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                
                parsed_count = 0
                for participant in participants:
                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO parsed_users (user_id, username, first_name, last_name, phone, bio, is_bot, is_verified, is_premium)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            str(participant.id),
                            participant.username or '',
                            participant.first_name or '',
                            participant.last_name or '',
                            participant.phone or '',
                            participant.about or '',
                            getattr(participant, 'bot', False),
                            getattr(participant, 'verified', False),
                            getattr(participant, 'premium', False)
                        ))
                        parsed_count += 1
                    except Exception as e:
                        logger.error(f"Ошибка сохранения участника: {e}")
                        continue
                
                conn.commit()
                conn.close()
                
                logger.info(f"Парсинг завершен: {parsed_count} участников из канала {channel_link}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка парсинга канала {channel_link}: {e}")
            return False
    
    def get_active_account(self):
        """Получение активного аккаунта для парсинга"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.id, a.session_file, a.api_id, a.api_hash, p.ip, p.port, p.username, p.password
                FROM accounts a
                LEFT JOIN proxies p ON a.proxy_id = p.id
                WHERE a.status = 'online' AND a.api_id IS NOT NULL
                ORDER BY RANDOM()
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                account = {
                    'id': result[0],
                    'session_file': result[1],
                    'api_id': result[2],
                    'api_hash': result[3],
                    'proxy': None
                }
                
                if result[4]:
                    account['proxy'] = {
                        'ip': result[4], 'port': result[5],
                        'username': result[6], 'password': result[7]
                    }
                
                return account
            
            return None
        except Exception as e:
            logger.error(f"Ошибка получения активного аккаунта: {e}")
            return None
    
    def analyze_audience(self, task_id):
        """Анализ собранной аудитории"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Получаем всех пользователей из задачи
            cursor.execute('''
                SELECT username, first_name, last_name, phone, bio, is_bot, is_verified, 
                       is_premium, last_seen, common_chats_count
                FROM parsed_users WHERE task_id = ?
            ''', (task_id,))
            
            users = cursor.fetchall()
            
            if not users:
                return None
            
            # Анализируем данные
            analysis = {
                'total_users': len(users),
                'with_username': sum(1 for user in users if user[0]),
                'with_phone': sum(1 for user in users if user[3]),
                'with_bio': sum(1 for user in users if user[4]),
                'bots': sum(1 for user in users if user[5]),
                'verified': sum(1 for user in users if user[6]),
                'premium': sum(1 for user in users if user[7]),
                'active_users': sum(1 for user in users if user[8] and user[8] > 0),
                'common_chats': sum(user[9] for user in users if user[9]),
                'gender_analysis': self.analyze_gender(users),
                'name_analysis': self.analyze_names(users),
                'bio_analysis': self.analyze_bios(users),
                'activity_analysis': self.analyze_activity(users)
            }
            
            conn.close()
            return analysis
            
        except Exception as e:
            logger.error(f"Ошибка анализа аудитории: {e}")
            return None
    
    def analyze_gender(self, users):
        """Анализ пола пользователей по именам"""
        male_names = ['Александр', 'Дмитрий', 'Максим', 'Сергей', 'Андрей', 'Алексей', 'Артём', 'Илья', 'Кирилл', 'Михаил',
                     'Alexander', 'Dmitry', 'Maxim', 'Sergey', 'Andrey', 'Alexey', 'Artem', 'Ilya', 'Kirill', 'Mikhail',
                     'John', 'Michael', 'David', 'James', 'Robert', 'William', 'Richard', 'Thomas', 'Christopher', 'Daniel']
        
        female_names = ['Анна', 'Мария', 'Елена', 'Наталья', 'Ольга', 'Татьяна', 'Ирина', 'Екатерина', 'Светлана', 'Юлия',
                       'Anna', 'Maria', 'Elena', 'Natalia', 'Olga', 'Tatiana', 'Irina', 'Ekaterina', 'Svetlana', 'Yulia',
                       'Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth', 'Barbara', 'Susan', 'Jessica', 'Sarah', 'Karen']
        
        male_count = 0
        female_count = 0
        unknown_count = 0
        
        for user in users:
            first_name = user[1] or ''
            last_name = user[2] or ''
            full_name = f"{first_name} {last_name}".strip()
            
            if any(name.lower() in full_name.lower() for name in male_names):
                male_count += 1
            elif any(name.lower() in full_name.lower() for name in female_names):
                female_count += 1
            else:
                unknown_count += 1
        
        total = len(users)
        return {
            'male': {'count': male_count, 'percentage': round(male_count / total * 100, 1)},
            'female': {'count': female_count, 'percentage': round(female_count / total * 100, 1)},
            'unknown': {'count': unknown_count, 'percentage': round(unknown_count / total * 100, 1)}
        }
    
    def analyze_names(self, users):
        """Анализ имен пользователей"""
        names = [user[1] for user in users if user[1]]
        last_names = [user[2] for user in users if user[2]]
        
        # Топ имен
        name_counts = {}
        for name in names:
            if name:
                name_counts[name] = name_counts.get(name, 0) + 1
        
        top_names = sorted(name_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Топ фамилий
        lastname_counts = {}
        for lastname in last_names:
            if lastname:
                lastname_counts[lastname] = lastname_counts.get(lastname, 0) + 1
        
        top_lastnames = sorted(lastname_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'top_names': top_names,
            'top_lastnames': top_lastnames,
            'unique_names': len(name_counts),
            'unique_lastnames': len(lastname_counts)
        }
    
    def analyze_bios(self, users):
        """Анализ биографий пользователей"""
        bios = [user[4] for user in users if user[4]]
        
        if not bios:
            return {'total_with_bio': 0, 'common_words': [], 'avg_length': 0}
        
        # Общие слова в биографиях
        all_words = []
        for bio in bios:
            words = bio.lower().split()
            all_words.extend(words)
        
        word_counts = {}
        for word in all_words:
            if len(word) > 3:  # Игнорируем короткие слова
                word_counts[word] = word_counts.get(word, 0) + 1
        
        common_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Средняя длина биографии
        avg_length = sum(len(bio) for bio in bios) / len(bios)
        
        return {
            'total_with_bio': len(bios),
            'common_words': common_words,
            'avg_length': round(avg_length, 1)
        }
    
    def analyze_activity(self, users):
        """Анализ активности пользователей"""
        active_users = [user for user in users if user[8]]  # last_seen
        common_chats = [user[9] for user in users if user[9]]  # common_chats_count
        
        if not active_users:
            return {'active_percentage': 0, 'avg_common_chats': 0}
        
        # Процент активных пользователей
        active_percentage = len(active_users) / len(users) * 100
        
        # Среднее количество общих чатов
        avg_common_chats = sum(common_chats) / len(common_chats) if common_chats else 0
        
        return {
            'active_percentage': round(active_percentage, 1),
            'avg_common_chats': round(avg_common_chats, 1),
            'high_activity_users': len([user for user in users if user[9] and user[9] > 5])
        }

class ReportGenerator:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def generate_accounts_report(self):
        """Генерация отчета по аккаунтам"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute('SELECT COUNT(*) FROM accounts')
            total_accounts = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM accounts WHERE status = "online"')
            online_accounts = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM accounts WHERE status = "banned"')
            banned_accounts = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM proxies WHERE is_active = 1')
            active_proxies = cursor.fetchone()[0]
            
            # Статистика по странам
            cursor.execute('SELECT geo_country, COUNT(*) FROM accounts WHERE geo_country IS NOT NULL GROUP BY geo_country')
            country_stats = cursor.fetchall()
            
            conn.close()
            
            report = {
                'total_accounts': total_accounts,
                'online_accounts': online_accounts,
                'banned_accounts': banned_accounts,
                'active_proxies': active_proxies,
                'country_distribution': dict(country_stats),
                'generated_at': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Ошибка генерации отчета: {e}")
            return None
    
    def generate_campaign_report(self, campaign_id):
        """Генерация отчета по кампании"""
        try:
            # Здесь должна быть логика получения данных кампании
            # Для демонстрации возвращаем базовую структуру
            report = {
                'campaign_id': campaign_id,
                'total_sent': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0,
                'generated_at': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Ошибка генерации отчета кампании: {e}")
            return None
    
    def export_report_to_csv(self, report_data, filename):
        """Экспорт отчета в CSV"""
        try:
            import csv
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Записываем заголовки
                writer.writerow(['Метрика', 'Значение'])
                
                # Записываем данные
                for key, value in report_data.items():
                    if key != 'generated_at':
                        writer.writerow([key, value])
            
            logger.info(f"Отчет экспортирован в {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта отчета: {e}")
            return False

class SpamManager:
    def __init__(self, db_manager, account_manager):
        self.db = db_manager
        self.account_manager = account_manager
        self.active_campaigns = {}
    
    def start_spam_campaign(self, campaign_data):
        """Запуск спам-кампании"""
        campaign_id = campaign_data.get('id', int(time.time()))
        
        # Получаем список юзернеймов для рассылки
        usernames = self.get_usernames_for_campaign(campaign_data)
        
        if not usernames:
            logger.error("Нет юзернеймов для рассылки")
            return False
        
        # Получаем активные аккаунты
        active_accounts = self.get_active_accounts()
        
        if not active_accounts:
            logger.error("Нет активных аккаунтов")
            return False
        
        # Создаем кампанию
        campaign = {
            'id': campaign_id,
            'name': campaign_data.get('name', f'Campaign_{campaign_id}'),
            'message': campaign_data.get('message', ''),
            'usernames': usernames,
            'accounts': active_accounts,
            'status': 'running',
            'sent_count': 0,
            'success_count': 0,
            'error_count': 0,
            'started_at': datetime.now().isoformat()
        }
        
        self.active_campaigns[campaign_id] = campaign
        
        # Запускаем рассылку в отдельном потоке
        thread = threading.Thread(target=self.run_spam_campaign, args=(campaign_id,))
        thread.daemon = True
        thread.start()
        
        logger.info(f"Запущена спам-кампания {campaign_id} на {len(usernames)} юзернеймов")
        return True
    
    def get_usernames_for_campaign(self, campaign_data):
        """Получение списка юзернеймов для рассылки"""
        usernames = []
        
        # Если указан файл с юзернеймами
        if campaign_data.get('usernames_file'):
            try:
                with open(campaign_data['usernames_file'], 'r', encoding='utf-8') as f:
                    for line in f:
                        username = line.strip()
                        if username and not username.startswith('#'):
                            if not username.startswith('@'):
                                username = '@' + username
                            usernames.append(username)
            except Exception as e:
                logger.error(f"Ошибка чтения файла юзернеймов: {e}")
        
        # Если указана база данных
        elif campaign_data.get('database'):
            try:
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT username FROM parsed_users WHERE username IS NOT NULL AND username != ""')
                results = cursor.fetchall()
                usernames = ['@' + row[0] if not row[0].startswith('@') else row[0] for row in results]
                conn.close()
            except Exception as e:
                logger.error(f"Ошибка получения юзернеймов из БД: {e}")
        
        return usernames
    
    def get_active_accounts(self):
        """Получение активных аккаунтов"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.id, a.session_file, a.api_id, a.api_hash, p.ip, p.port, p.username, p.password
                FROM accounts a
                LEFT JOIN proxies p ON a.proxy_id = p.id
                WHERE a.status = 'online' AND a.api_id IS NOT NULL
                ORDER BY RANDOM()
            ''')
            
            accounts = []
            for row in cursor.fetchall():
                account = {
                    'id': row[0],
                    'session_file': row[1],
                    'api_id': row[2],
                    'api_hash': row[3],
                    'proxy': None
                }
                
                if row[4]:  # Если есть прокси
                    account['proxy'] = {
                        'ip': row[4],
                        'port': row[5],
                        'username': row[6],
                        'password': row[7]
                    }
                
                accounts.append(account)
            
            conn.close()
            return accounts
        except Exception as e:
            logger.error(f"Ошибка получения активных аккаунтов: {e}")
            return []
    
    def run_spam_campaign(self, campaign_id):
        """Выполнение спам-кампании"""
        campaign = self.active_campaigns.get(campaign_id)
        if not campaign:
            return
        
        message = campaign['message']
        usernames = campaign['usernames']
        accounts = campaign['accounts']
        
        account_index = 0
        sent_count = 0
        
        for username in usernames:
            if campaign['status'] != 'running':
                break
            
            # Выбираем аккаунт
            account = accounts[account_index % len(accounts)]
            account_index += 1
            
            # Отправляем сообщение
            success = self.send_message(account, username, message)
            
            if success:
                campaign['success_count'] += 1
                logger.info(f"✅ Отправлено {username} через аккаунт {account['id']}")
            else:
                campaign['error_count'] += 1
                logger.error(f"❌ Ошибка отправки {username} через аккаунт {account['id']}")
            
            campaign['sent_count'] += 1
            sent_count += 1
            
            # Задержка между сообщениями
            delay = random.randint(3, 10)
            time.sleep(delay)
            
            # Задержка между аккаунтами
            if account_index % 10 == 0:
                time.sleep(random.randint(10, 30))
        
        campaign['status'] = 'completed'
        campaign['completed_at'] = datetime.now().isoformat()
        
        logger.info(f"Кампания {campaign_id} завершена. Отправлено: {campaign['success_count']}/{campaign['sent_count']}")
    
    def send_message(self, account, username, message):
        """Отправка сообщения"""
        try:
            client = TelegramClient(account['session_file'], account['api_id'], account['api_hash'])
            
            # Настраиваем прокси если есть
            if account['proxy']:
                proxy = {
                    'proxy_type': 'http',
                    'addr': account['proxy']['ip'],
                    'port': account['proxy']['port'],
                    'username': account['proxy']['username'],
                    'password': account['proxy']['password']
                }
                client.set_proxy(proxy)
            
            with client:
                # Отправляем сообщение
                client.send_message(username, message)
                return True
                
        except FloodWaitError as e:
            logger.warning(f"FloodWait для аккаунта {account['id']}: {e.seconds} сек")
            time.sleep(min(e.seconds, 300))  # Максимум 5 минут ожидания
            return False
        except UserBannedError:
            logger.warning(f"Пользователь {username} заблокировал бота")
            self.add_to_blacklist(username, 'USER_BANNED')
            return False
        except ChatWriteForbiddenError:
            logger.warning(f"Нельзя писать в чат {username}")
            self.add_to_blacklist(username, 'CHAT_FORBIDDEN')
            return False
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения {username}: {e}")
            return False
    
    def add_to_blacklist(self, username, reason):
        """Добавление в blacklist"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO blacklist (user_id, username, reason)
                VALUES (?, ?, ?)
            ''', (username, username, reason))
            conn.commit()
            conn.close()
            logger.info(f"Добавлен в blacklist: {username} (причина: {reason})")
        except Exception as e:
            logger.error(f"Ошибка добавления в blacklist: {e}")
    
    def stop_campaign(self, campaign_id):
        """Остановка кампании"""
        if campaign_id in self.active_campaigns:
            self.active_campaigns[campaign_id]['status'] = 'stopped'
            logger.info(f"Кампания {campaign_id} остановлена")
            return True
        return False
    
    def get_campaign_stats(self, campaign_id):
        """Получение статистики кампании"""
        return self.active_campaigns.get(campaign_id, {})

# Инициализация менеджеров
db_manager = DatabaseManager()
proxy_manager = ProxyManager(db_manager)
account_manager = AccountManager(db_manager, proxy_manager)
spam_manager = SpamManager(db_manager, account_manager)
registration_manager = AccountRegistrationManager(db_manager)
account_management_manager = AccountManagementManager(db_manager)
invitation_manager = InvitationManager(db_manager, account_manager)
subscription_manager = SubscriptionManager(db_manager, account_manager)
session_cloning_manager = SessionCloningManager(db_manager)
parsing_manager = ParsingManager(db_manager)
report_generator = ReportGenerator(db_manager)

# Импорт конфигурации
from config import config

# Получение конфигурации
config_name = os.environ.get('FLASK_ENV', 'default')
app_config = config[config_name]

# API ключи будут извлекаться из сессий автоматически
api_id = None
api_hash = None

def extract_api_from_session(session_file):
    """Извлечение API ключей из файла сессии"""
    try:
        import sqlite3
        conn = sqlite3.connect(session_file)
        cursor = conn.cursor()
        
        # Получаем API данные из сессии
        cursor.execute("SELECT api_id, api_hash FROM sessions WHERE dc_id = 2")
        result = cursor.fetchone()
        
        if result and result[0] and result[1]:
            conn.close()
            return result[0], result[1]
        
        # Пробуем альтернативный способ
        cursor.execute("SELECT api_id, api_hash FROM sessions LIMIT 1")
        result = cursor.fetchone()
        
        if result and result[0] and result[1]:
            conn.close()
            return result[0], result[1]
        
        conn.close()
        return None, None
    except Exception as e:
        logger.error(f"Ошибка извлечения API из сессии {session_file}: {e}")
        return None, None

@app.route('/')
def index():
    """Главная страница - дашборд"""
    return render_template('index.html')

@app.route('/accounts')
def accounts_page():
    """Страница управления аккаунтами"""
    return render_template('accounts.html')

@app.route('/parsing')
def parsing_page():
    """Страница парсинга"""
    return render_template('parsing.html')

@app.route('/campaigns')
def campaigns_page():
    """Страница рассылок"""
    return render_template('campaigns.html')

@app.route('/blacklist')
def blacklist_page():
    """Страница blacklist"""
    return render_template('blacklist.html')

@app.route('/registration')
def registration_page():
    """Страница регистрации аккаунтов"""
    return render_template('registration.html')

@app.route('/invitations')
def invitations_page():
    """Страница массовых приглашений"""
    return render_template('invitations.html')

@app.route('/subscriptions')
def subscriptions_page():
    """Страница массовых подписок"""
    return render_template('subscriptions.html')

@app.route('/settings')
def settings_page():
    """Страница настроек"""
    return render_template('settings.html')

# API endpoints
@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Получение списка аккаунтов"""
    try:
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, a.phone, a.username, a.first_name, a.last_name, 
                   a.status, a.geo_country, p.ip, p.port
            FROM accounts a
            LEFT JOIN proxies p ON a.proxy_id = p.id
            ORDER BY a.id
        ''')
        
        accounts = []
        for row in cursor.fetchall():
            accounts.append({
                'id': row[0],
                'phone': row[1],
                'username': row[2] or '',
                'first_name': row[3] or '',
                'last_name': row[4] or '',
                'status': row[5],
                'geo_country': row[6] or '',
                'proxy': f"{row[7]}:{row[8]}" if row[7] else ''
            })
        
        conn.close()
        return jsonify(accounts)
    except Exception as e:
        logger.error(f"Ошибка получения аккаунтов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-sessions', methods=['POST'])
def upload_sessions():
    """Загрузка сессий из папки"""
    try:
        folder_path = request.json.get('folder_path')
        if not folder_path or not os.path.exists(folder_path):
            return jsonify({'error': 'Неверный путь к папке'}), 400
        
        count = account_manager.load_sessions_from_folder(folder_path)
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Ошибка загрузки сессий: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-proxies', methods=['POST'])
def upload_proxies():
    """Загрузка прокси из файла"""
    try:
        file_path = request.json.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'Неверный путь к файлу'}), 400
        
        count = proxy_manager.load_proxies_from_file(file_path)
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Ошибка загрузки прокси: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-proxies-api', methods=['POST'])
def get_proxies_api():
    """Получение прокси через API"""
    try:
        api_key = request.json.get('api_key')
        if not api_key:
            return jsonify({'error': 'API ключ не указан'}), 400
        
        count = proxy_manager.get_proxies_from_api(api_key)
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Ошибка получения прокси из API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/assign-geo-proxies', methods=['POST'])
def assign_geo_proxies():
    """Назначение прокси по геолокации"""
    try:
        country = request.json.get('country')
        if not country:
            return jsonify({'error': 'Страна не указана'}), 400
        
        count = account_manager.assign_geo_proxies(country)
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Ошибка назначения гео-прокси: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mass-check', methods=['POST'])
def mass_check():
    """Массовая проверка аккаунтов"""
    try:
        count = account_manager.mass_check_accounts()
        return jsonify({'success': True, 'count': count, 'message': f'Запущена проверка {count} аккаунтов'})
    except Exception as e:
        logger.error(f"Ошибка массовой проверки: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Получение статистики"""
    try:
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        # Общая статистика аккаунтов
        cursor.execute('SELECT COUNT(*) FROM accounts')
        total_accounts = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM accounts WHERE status = "online"')
        online_accounts = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM accounts WHERE status = "banned"')
        banned_accounts = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM proxies WHERE is_active = 1')
        active_proxies = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_accounts': total_accounts,
            'online_accounts': online_accounts,
            'banned_accounts': banned_accounts,
            'active_proxies': active_proxies
        })
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/start-spam', methods=['POST'])
def start_spam():
    """Запуск спам-кампании"""
    try:
        campaign_data = request.json
        
        # Валидация данных
        if not campaign_data.get('message'):
            return jsonify({'error': 'Сообщение не указано'}), 400
        
        if not campaign_data.get('usernames_file') and not campaign_data.get('database'):
            return jsonify({'error': 'Не указан источник юзернеймов'}), 400
        
        # Запускаем кампанию
        success = spam_manager.start_spam_campaign(campaign_data)
        
        if success:
            return jsonify({'success': True, 'message': 'Спам-кампания запущена'})
        else:
            return jsonify({'error': 'Не удалось запустить кампанию'}), 500
            
    except Exception as e:
        logger.error(f"Ошибка запуска спам-кампании: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop-spam/<int:campaign_id>', methods=['POST'])
def stop_spam(campaign_id):
    """Остановка спам-кампании"""
    try:
        success = spam_manager.stop_campaign(campaign_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Кампания остановлена'})
        else:
            return jsonify({'error': 'Кампания не найдена'}), 404
            
    except Exception as e:
        logger.error(f"Ошибка остановки кампании: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/spam-stats/<int:campaign_id>', methods=['GET'])
def get_spam_stats(campaign_id):
    """Получение статистики спам-кампании"""
    try:
        stats = spam_manager.get_campaign_stats(campaign_id)
        
        if stats:
            return jsonify(stats)
        else:
            return jsonify({'error': 'Кампания не найдена'}), 404
            
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-sessions', methods=['POST'])
def upload_sessions():
    """Загрузка сессий из папки"""
    try:
        data = request.json
        folder_path = data.get('folder_path')
        
        if not folder_path:
            return jsonify({'error': 'Не указан путь к папке'}), 400
        
        # Загружаем сессии через AccountManager
        count = account_manager.load_sessions_from_folder(folder_path)
        
        return jsonify({
            'success': True,
            'count': count,
            'message': f'Загружено {count} сессий'
        })
        
    except Exception as e:
        logger.error(f"Ошибка загрузки сессий: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-usernames', methods=['POST'])
def upload_usernames():
    """Загрузка файла с юзернеймами"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не выбран'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        # Сохраняем файл
        filename = f"usernames_{int(time.time())}.txt"
        filepath = os.path.join('uploads', filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(filepath)
        
        # Подсчитываем количество юзернеймов
        count = 0
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    count += 1
        
        return jsonify({
            'success': True, 
            'filename': filename,
            'filepath': filepath,
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Ошибка загрузки файла юзернеймов: {e}")
        return jsonify({'error': str(e)}), 500

# API endpoints для новых функций

@app.route('/api/register-accounts', methods=['POST'])
def register_accounts():
    """Массовая регистрация аккаунтов"""
    try:
        data = request.json
        phone_numbers = data.get('phone_numbers', [])
        api_id = data.get('api_id')
        api_hash = data.get('api_hash')
        sms_service = data.get('sms_service', 'sms-activate')
        
        if not phone_numbers or not api_id or not api_hash:
            return jsonify({'error': 'Не указаны номера телефонов или API ключи'}), 400
        
        result = registration_manager.mass_registration(phone_numbers, api_id, api_hash, sms_service)
        return jsonify({'success': True, 'result': result})
        
    except Exception as e:
        logger.error(f"Ошибка регистрации аккаунтов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-profiles', methods=['POST'])
def update_profiles():
    """Массовое обновление профилей аккаунтов"""
    try:
        data = request.json
        account_ids = data.get('account_ids', [])
        profile_data = data.get('profile_data', {})
        
        if not account_ids or not profile_data:
            return jsonify({'error': 'Не указаны ID аккаунтов или данные профиля'}), 400
        
        success_count = account_management_manager.mass_update_profiles(account_ids, profile_data)
        return jsonify({'success': True, 'updated_count': success_count})
        
    except Exception as e:
        logger.error(f"Ошибка обновления профилей: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/send-invitations', methods=['POST'])
def send_invitations():
    """Отправка массовых приглашений"""
    try:
        data = request.json
        target_usernames = data.get('usernames', [])
        chat_link = data.get('chat_link')
        message = data.get('message', 'Приглашаю вас в наш чат!')
        
        if not target_usernames or not chat_link:
            return jsonify({'error': 'Не указаны юзернеймы или ссылка на чат'}), 400
        
        result = invitation_manager.send_invitations(target_usernames, chat_link, message)
        return jsonify({'success': True, 'result': result})
        
    except Exception as e:
        logger.error(f"Ошибка отправки приглашений: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mass-subscribe', methods=['POST'])
def mass_subscribe():
    """Массовая подписка на каналы"""
    try:
        data = request.json
        target_channels = data.get('channels', [])
        account_ids = data.get('account_ids')
        
        if not target_channels:
            return jsonify({'error': 'Не указаны каналы для подписки'}), 400
        
        result = subscription_manager.mass_subscribe(target_channels, account_ids)
        return jsonify({'success': True, 'result': result})
        
    except Exception as e:
        logger.error(f"Ошибка массовой подписки: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clone-sessions', methods=['POST'])
def clone_sessions():
    """Клонирование сессий"""
    try:
        data = request.json
        original_session_path = data.get('original_session_path')
        phone_numbers = data.get('phone_numbers', [])
        api_id = data.get('api_id')
        api_hash = data.get('api_hash')
        
        if not original_session_path or not phone_numbers or not api_id or not api_hash:
            return jsonify({'error': 'Не указаны все необходимые параметры'}), 400
        
        success_count = session_cloning_manager.mass_clone_sessions(
            original_session_path, phone_numbers, api_id, api_hash
        )
        return jsonify({'success': True, 'cloned_count': success_count})
        
    except Exception as e:
        logger.error(f"Ошибка клонирования сессий: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-report', methods=['GET'])
def generate_report():
    """Генерация отчета"""
    try:
        report_type = request.args.get('type', 'accounts')
        
        if report_type == 'accounts':
            report = report_generator.generate_accounts_report()
        else:
            return jsonify({'error': 'Неизвестный тип отчета'}), 400
        
        if report:
            return jsonify({'success': True, 'report': report})
        else:
            return jsonify({'error': 'Ошибка генерации отчета'}), 500
            
    except Exception as e:
        logger.error(f"Ошибка генерации отчета: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-report', methods=['POST'])
def export_report():
    """Экспорт отчета в CSV"""
    try:
        data = request.json
        report_data = data.get('report_data')
        filename = data.get('filename', f'report_{int(time.time())}.csv')
        
        if not report_data:
            return jsonify({'error': 'Нет данных для экспорта'}), 400
        
        success = report_generator.export_report_to_csv(report_data, filename)
        
        if success:
            return jsonify({'success': True, 'filename': filename})
        else:
            return jsonify({'error': 'Ошибка экспорта отчета'}), 500
            
    except Exception as e:
        logger.error(f"Ошибка экспорта отчета: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/parse-channel', methods=['POST'])
def parse_channel():
    """Парсинг канала"""
    try:
        data = request.json
        channel_link = data.get('channel_link')
        max_users = data.get('max_users', 1000)
        
        if not channel_link:
            return jsonify({'error': 'Не указана ссылка на канал'}), 400
        
        success = parsing_manager.parse_channel(channel_link, max_users)
        
        if success:
            return jsonify({'success': True, 'message': 'Парсинг запущен'})
        else:
            return jsonify({'error': 'Не удалось запустить парсинг'}), 500
            
    except Exception as e:
        logger.error(f"Ошибка парсинга канала: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-audience/<int:task_id>', methods=['GET'])
def analyze_audience(task_id):
    """Анализ собранной аудитории"""
    try:
        analysis = parsing_manager.analyze_audience(task_id)
        
        if analysis:
            return jsonify({'success': True, 'analysis': analysis})
        else:
            return jsonify({'error': 'Не удалось проанализировать аудиторию'}), 500
            
    except Exception as e:
        logger.error(f"Ошибка анализа аудитории: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Запуск Telegram Mass Account Management Platform")
    logger.info(f"Платформа доступна по адресу: http://{app_config.HOST}:{app_config.PORT}")
    app.run(host=app_config.HOST, port=app_config.PORT, debug=app_config.DEBUG)