import os
import logging

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'cryptolens-v1-secret-key-change-in-production')
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    CRYPTO_DATA_FILE = os.path.join(DATA_DIR, 'crypto_data.json')
    USERS_FILE = os.path.join(DATA_DIR, 'users.json')
    FERNET_KEY_FILE = os.path.join(DATA_DIR, '.fernet_key')

    # Session / Cookie
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 86400  # 1 day
    WTF_CSRF_ENABLED = True

    # Scheduler
    SCHEDULER_INTERVAL_SECONDS = 60  # live-tick interval

    # Logging
    LOG_LEVEL = logging.INFO
    LOG_FILE = os.path.join(BASE_DIR, 'cryptolens.log')

    # Supported coins
    SUPPORTED_COINS = [
        'BTC', 'ETH', 'BNB', 'SOL', 'XRP',
        'ADA', 'DOGE', 'DOT', 'AVAX', 'MATIC'
    ]
