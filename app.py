"""
CryptoLens v1.0.0 – Main Flask Application
Developed by AVIK
Enterprise-grade cryptocurrency analysis & forecasting dashboard.
"""

import os
import io
import csv
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

from flask import (
    Flask, render_template, redirect, url_for, request,
    flash, jsonify, Response, session
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler

from config import Config
from models.data_engine import (
    generate_all_historical_data, update_live_tick,
    load_data, get_coin_data, COIN_PROFILES
)
from models.user_model import (
    User, create_user, get_user_by_id, authenticate
)
from models.predictor import predict

# ── App Factory ──────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config.from_object(Config)

# CSRF Protection
csrf = CSRFProtect(app)

# Logging
os.makedirs(os.path.dirname(Config.LOG_FILE), exist_ok=True) if os.path.dirname(Config.LOG_FILE) else None
handler = RotatingFileHandler(Config.LOG_FILE, maxBytes=2_000_000, backupCount=3)
handler.setLevel(Config.LOG_LEVEL)
handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
))
app.logger.addHandler(handler)
logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id, Config.USERS_FILE, Config.FERNET_KEY_FILE)


# ── Data Initialization ─────────────────────────────────────────────────────

def init_data():
    """Generate historical data if it doesn't exist."""
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    if not os.path.exists(Config.CRYPTO_DATA_FILE):
        logger.info('First run – generating historical crypto data …')
        generate_all_historical_data(Config.CRYPTO_DATA_FILE)
    else:
        logger.info('Crypto data file found.')


# ── Background Scheduler ────────────────────────────────────────────────────

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(
    func=lambda: update_live_tick(Config.CRYPTO_DATA_FILE),
    trigger='interval',
    seconds=Config.SCHEDULER_INTERVAL_SECONDS,
    id='live_tick',
    replace_existing=True,
)


# ── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template('login.html')
        user = authenticate(username, password, Config.USERS_FILE, Config.FERNET_KEY_FILE)
        if user:
            login_user(user, remember=request.form.get('remember'))
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        # Input validation
        errors = []
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')
        # XSS prevention – disallow HTML tags
        for field in [username, email]:
            if '<' in field or '>' in field:
                errors.append('Invalid characters in input.')
                break
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('signup.html')

        try:
            user = create_user(username, email, password,
                               Config.USERS_FILE, Config.FERNET_KEY_FILE)
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
        except ValueError as e:
            flash(str(e), 'danger')
    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


# ── Dashboard Routes ─────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    coins = []
    try:
        data = load_data(Config.CRYPTO_DATA_FILE)
        for symbol in Config.SUPPORTED_COINS:
            series = data.get(symbol, [])
            if len(series) >= 2:
                latest = series[-1]
                prev = series[-2]
                change = ((latest['close'] - prev['close']) / prev['close']) * 100
                coins.append({
                    'symbol': symbol,
                    'name': COIN_PROFILES[symbol]['name'],
                    'price': latest['close'],
                    'change': round(change, 2),
                    'volume': latest['volume'],
                    'market_cap': latest['market_cap'],
                })
    except Exception as e:
        logger.error(f'Dashboard data error: {e}')
    return render_template('dashboard.html', coins=coins, supported=Config.SUPPORTED_COINS)


@app.route('/coin/<symbol>')
@login_required
def coin_detail(symbol):
    symbol = symbol.upper()
    if symbol not in Config.SUPPORTED_COINS:
        return render_template('404.html'), 404
    profile = COIN_PROFILES.get(symbol, {})
    return render_template('coin_detail.html', symbol=symbol, profile=profile,
                           supported=Config.SUPPORTED_COINS)


# ── Prediction Routes ───────────────────────────────────────────────────────

@app.route('/predictions')
@login_required
def predictions():
    return render_template('prediction.html', supported=Config.SUPPORTED_COINS)


# ── API Endpoints ────────────────────────────────────────────────────────────

@app.route('/api/data/<symbol>')
@login_required
def api_data(symbol):
    """Return OHLCV JSON for a coin."""
    symbol = symbol.upper()
    if symbol not in Config.SUPPORTED_COINS:
        return jsonify({'error': 'Unsupported coin'}), 404
    try:
        series = get_coin_data(Config.CRYPTO_DATA_FILE, symbol)
        return jsonify({
            'symbol': symbol,
            'name': COIN_PROFILES[symbol]['name'],
            'data': series[-365:]  # last year by default
        })
    except Exception as e:
        logger.error(f'API data error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/data/<symbol>/all')
@login_required
def api_data_all(symbol):
    """Return full OHLCV JSON for a coin."""
    symbol = symbol.upper()
    if symbol not in Config.SUPPORTED_COINS:
        return jsonify({'error': 'Unsupported coin'}), 404
    try:
        series = get_coin_data(Config.CRYPTO_DATA_FILE, symbol)
        return jsonify({
            'symbol': symbol,
            'name': COIN_PROFILES[symbol]['name'],
            'data': series
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/predictions/<symbol>')
@login_required
def api_predictions(symbol):
    """Return ML predictions for a coin."""
    symbol = symbol.upper()
    days = request.args.get('days', 7, type=int)
    days = min(max(days, 1), 30)
    if symbol not in Config.SUPPORTED_COINS:
        return jsonify({'error': 'Unsupported coin'}), 404
    try:
        series = get_coin_data(Config.CRYPTO_DATA_FILE, symbol)
        result = predict(series, symbol, days)
        return jsonify(result)
    except Exception as e:
        logger.error(f'Prediction error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/correlation')
@login_required
def api_correlation():
    """Return correlation matrix data for all coins."""
    try:
        data = load_data(Config.CRYPTO_DATA_FILE)
        import pandas as pd
        closes = {}
        for symbol in Config.SUPPORTED_COINS:
            series = data.get(symbol, [])
            if series:
                df = pd.DataFrame(series)
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                closes[symbol] = df['close']
        df_all = pd.DataFrame(closes)
        # Use last 365 days of common dates
        df_all = df_all.dropna().tail(365)
        corr = df_all.corr().round(4)
        return jsonify({
            'symbols': corr.columns.tolist(),
            'matrix': corr.values.tolist()
        })
    except Exception as e:
        logger.error(f'Correlation error: {e}')
        return jsonify({'error': str(e)}), 500


# ── Export Endpoints ─────────────────────────────────────────────────────────

@app.route('/api/export/csv')
@login_required
def export_csv():
    """Export OHLCV data as CSV download."""
    symbol = request.args.get('coin', 'BTC').upper()
    if symbol not in Config.SUPPORTED_COINS:
        return jsonify({'error': 'Unsupported coin'}), 404
    try:
        series = get_coin_data(Config.CRYPTO_DATA_FILE, symbol)
        output = io.StringIO()
        writer = csv.DictWriter(output,
                                fieldnames=['date', 'open', 'high', 'low', 'close', 'volume', 'market_cap'])
        writer.writeheader()
        writer.writerows(series)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={symbol}_data.csv'}
        )
    except Exception as e:
        logger.error(f'CSV export error: {e}')
        return jsonify({'error': str(e)}), 500


# ── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_data()
    scheduler.start()
    logger.info('CryptoLens v1.0.0 starting …')
    app.run(debug=True, use_reloader=False, port=5000)
