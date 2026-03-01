"""
CryptoLens – User Model with Encrypted JSON Storage
Passwords hashed with Werkzeug, JSON file encrypted at rest with Fernet.
"""

import json
import os
import uuid
import logging
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from flask_login import UserMixin

logger = logging.getLogger(__name__)


class User(UserMixin):
    """Flask-Login compatible user object."""

    def __init__(self, id, username, email, password_hash, role='user', created_at=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role  # 'admin' or 'user'
        self.created_at = created_at or datetime.utcnow().isoformat()

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'role': self.role,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_dict(d: dict) -> 'User':
        return User(
            id=d['id'],
            username=d['username'],
            email=d['email'],
            password_hash=d['password_hash'],
            role=d.get('role', 'user'),
            created_at=d.get('created_at'),
        )


# ── Encrypted JSON Helpers ──────────────────────────────────────────────────

def _get_fernet(key_file: str) -> Fernet:
    """Load or generate a Fernet key for encrypting the users JSON."""
    os.makedirs(os.path.dirname(key_file), exist_ok=True)
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        logger.info('Generated new Fernet encryption key.')
    return Fernet(key)


def _read_users(users_file: str, key_file: str) -> list[dict]:
    """Decrypt and parse the users JSON file."""
    if not os.path.exists(users_file):
        return []
    fernet = _get_fernet(key_file)
    with open(users_file, 'rb') as f:
        encrypted = f.read()
    if not encrypted:
        return []
    try:
        decrypted = fernet.decrypt(encrypted)
        return json.loads(decrypted.decode('utf-8'))
    except Exception as e:
        logger.error(f'Failed to decrypt users file: {e}')
        return []


def _write_users(users: list[dict], users_file: str, key_file: str) -> None:
    """Encrypt and write the users list to JSON."""
    fernet = _get_fernet(key_file)
    data = json.dumps(users, separators=(',', ':')).encode('utf-8')
    encrypted = fernet.encrypt(data)
    os.makedirs(os.path.dirname(users_file), exist_ok=True)
    with open(users_file, 'wb') as f:
        f.write(encrypted)


# ── Public CRUD API ─────────────────────────────────────────────────────────

def create_user(username: str, email: str, password: str,
                users_file: str, key_file: str, role: str = 'user') -> User:
    """Register a new user. Raises ValueError on duplicate username/email."""
    users = _read_users(users_file, key_file)
    for u in users:
        if u['username'].lower() == username.lower():
            raise ValueError('Username already exists.')
        if u['email'].lower() == email.lower():
            raise ValueError('Email already registered.')

    user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        password_hash=generate_password_hash(password, method='pbkdf2:sha256'),
        role=role,
    )
    users.append(user.to_dict())
    _write_users(users, users_file, key_file)
    logger.info(f'User created: {username} ({role})')
    return user


def get_user_by_id(user_id: str, users_file: str, key_file: str):
    """Retrieve a User by id, or None."""
    users = _read_users(users_file, key_file)
    for u in users:
        if u['id'] == user_id:
            return User.from_dict(u)
    return None


def get_user_by_username(username: str, users_file: str, key_file: str):
    """Retrieve a User by username, or None."""
    users = _read_users(users_file, key_file)
    for u in users:
        if u['username'].lower() == username.lower():
            return User.from_dict(u)
    return None


def authenticate(username: str, password: str, users_file: str, key_file: str):
    """Return User if credentials valid, else None."""
    user = get_user_by_username(username, users_file, key_file)
    if user and user.check_password(password):
        return user
    return None
