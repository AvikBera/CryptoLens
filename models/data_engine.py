"""
CryptoLens – Custom Crypto Data Generation & Aggregation Engine
Generates realistic OHLCV + Market Cap historical data from 2009 onward.
No third-party APIs used. All data is algorithmically simulated.
"""

import json
import os
import math
import random
import tempfile
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ── Coin Profiles ────────────────────────────────────────────────────────────
# Each coin has a launch date, initial price, and volatility characteristics.
COIN_PROFILES = {
    'BTC': {
        'name': 'Bitcoin', 'symbol': 'BTC', 'launch': '2009-01-03',
        'init_price': 0.01, 'volatility': 0.04, 'drift': 0.0012,
        'max_cap_factor': 1_200_000_000_000, 'volume_base': 30_000_000_000
    },
    'ETH': {
        'name': 'Ethereum', 'symbol': 'ETH', 'launch': '2015-07-30',
        'init_price': 0.75, 'volatility': 0.05, 'drift': 0.0010,
        'max_cap_factor': 400_000_000_000, 'volume_base': 15_000_000_000
    },
    'BNB': {
        'name': 'Binance Coin', 'symbol': 'BNB', 'launch': '2017-07-25',
        'init_price': 0.10, 'volatility': 0.045, 'drift': 0.0009,
        'max_cap_factor': 80_000_000_000, 'volume_base': 2_000_000_000
    },
    'SOL': {
        'name': 'Solana', 'symbol': 'SOL', 'launch': '2020-03-16',
        'init_price': 0.50, 'volatility': 0.06, 'drift': 0.0015,
        'max_cap_factor': 60_000_000_000, 'volume_base': 3_000_000_000
    },
    'XRP': {
        'name': 'Ripple', 'symbol': 'XRP', 'launch': '2013-08-04',
        'init_price': 0.005, 'volatility': 0.05, 'drift': 0.0006,
        'max_cap_factor': 50_000_000_000, 'volume_base': 2_500_000_000
    },
    'ADA': {
        'name': 'Cardano', 'symbol': 'ADA', 'launch': '2017-10-01',
        'init_price': 0.02, 'volatility': 0.055, 'drift': 0.0007,
        'max_cap_factor': 30_000_000_000, 'volume_base': 1_000_000_000
    },
    'DOGE': {
        'name': 'Dogecoin', 'symbol': 'DOGE', 'launch': '2013-12-06',
        'init_price': 0.0002, 'volatility': 0.06, 'drift': 0.0005,
        'max_cap_factor': 25_000_000_000, 'volume_base': 1_500_000_000
    },
    'DOT': {
        'name': 'Polkadot', 'symbol': 'DOT', 'launch': '2020-05-26',
        'init_price': 2.50, 'volatility': 0.05, 'drift': 0.0008,
        'max_cap_factor': 20_000_000_000, 'volume_base': 800_000_000
    },
    'AVAX': {
        'name': 'Avalanche', 'symbol': 'AVAX', 'launch': '2020-09-21',
        'init_price': 3.00, 'volatility': 0.055, 'drift': 0.0009,
        'max_cap_factor': 15_000_000_000, 'volume_base': 600_000_000
    },
    'MATIC': {
        'name': 'Polygon', 'symbol': 'MATIC', 'launch': '2019-04-26',
        'init_price': 0.003, 'volatility': 0.06, 'drift': 0.0010,
        'max_cap_factor': 12_000_000_000, 'volume_base': 500_000_000
    },
}

# Circulating supply approximations (used for market-cap calculation)
SUPPLY = {
    'BTC': 19_500_000, 'ETH': 120_000_000, 'BNB': 150_000_000,
    'SOL': 430_000_000, 'XRP': 53_000_000_000, 'ADA': 35_000_000_000,
    'DOGE': 142_000_000_000, 'DOT': 1_300_000_000, 'AVAX': 370_000_000,
    'MATIC': 10_000_000_000,
}


def _generate_coin_series(profile: dict, end_date: datetime) -> list[dict]:
    """Generate daily OHLCV candles for a single coin using geometric Brownian motion."""
    random.seed(hash(profile['symbol']))
    launch = datetime.strptime(profile['launch'], '%Y-%m-%d')
    if launch > end_date:
        return []

    price = profile['init_price']
    vol = profile['volatility']
    drift = profile['drift']
    supply = SUPPLY[profile['symbol']]
    vol_base = profile['volume_base']
    records = []
    day = launch

    # Pre-compute market-cycle periods (simulate bull/bear runs)
    cycle_len = 1460  # ~4 years in days
    while day <= end_date:
        day_index = (day - launch).days
        # Cycle modulation: bull/bear phases
        cycle_phase = math.sin(2 * math.pi * day_index / cycle_len)
        adjusted_drift = drift + 0.002 * cycle_phase

        # Geometric Brownian Motion step
        shock = random.gauss(0, 1)
        daily_return = adjusted_drift + vol * shock
        price *= math.exp(daily_return)
        price = max(price, profile['init_price'] * 0.001)  # floor

        # OHLCV
        intra_vol = vol * 0.6
        open_p = price * (1 + random.gauss(0, intra_vol * 0.3))
        high_p = price * (1 + abs(random.gauss(0, intra_vol)))
        low_p = price * (1 - abs(random.gauss(0, intra_vol)))
        close_p = price
        open_p = max(open_p, 0.000001)
        high_p = max(high_p, max(open_p, close_p))
        low_p = max(low_p, 0.000001)
        low_p = min(low_p, min(open_p, close_p))
        volume = vol_base * (0.5 + random.random()) * (1 + abs(daily_return) * 10)
        market_cap = close_p * supply

        records.append({
            'date': day.strftime('%Y-%m-%d'),
            'open': round(open_p, 6),
            'high': round(high_p, 6),
            'low': round(low_p, 6),
            'close': round(close_p, 6),
            'volume': round(volume, 2),
            'market_cap': round(market_cap, 2),
        })
        day += timedelta(days=1)

    return records


def generate_all_historical_data(data_file: str) -> dict:
    """Generate full historical OHLCV data for all supported coins and write to JSON."""
    logger.info('Generating historical crypto data …')
    end_date = datetime.utcnow() - timedelta(days=1)
    data = {}
    for symbol, profile in COIN_PROFILES.items():
        series = _generate_coin_series(profile, end_date)
        data[symbol] = series
        logger.info(f'  {symbol}: {len(series)} daily records generated')

    _atomic_write_json(data_file, data)
    logger.info(f'Data written to {data_file}')
    return data


def update_live_tick(data_file: str) -> None:
    """Append one new daily candle for each coin (called by scheduler)."""
    try:
        data = load_data(data_file)
    except Exception:
        logger.warning('Live tick: data file missing, regenerating.')
        data = generate_all_historical_data(data_file)
        return

    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    for symbol, profile in COIN_PROFILES.items():
        series = data.get(symbol, [])
        if series and series[-1]['date'] == today_str:
            # Already have today's candle – update close in-place
            last = series[-1]
            vol = profile['volatility']
            shock = random.gauss(0, 1)
            new_close = last['close'] * math.exp(0.0001 + vol * 0.3 * shock)
            new_close = max(new_close, 0.000001)
            last['close'] = round(new_close, 6)
            last['high'] = round(max(last['high'], new_close), 6)
            last['low'] = round(min(last['low'], new_close), 6)
            last['volume'] += round(profile['volume_base'] * 0.01 * random.random(), 2)
            last['market_cap'] = round(new_close * SUPPLY[symbol], 2)
            continue

        # Generate new candle
        if series:
            prev_close = series[-1]['close']
        else:
            prev_close = profile['init_price']

        vol = profile['volatility']
        shock = random.gauss(0, 1)
        daily_return = profile['drift'] + vol * shock
        close_p = prev_close * math.exp(daily_return)
        close_p = max(close_p, 0.000001)
        intra_vol = vol * 0.6
        open_p = prev_close * (1 + random.gauss(0, intra_vol * 0.3))
        high_p = max(close_p, open_p) * (1 + abs(random.gauss(0, intra_vol * 0.5)))
        low_p = min(close_p, open_p) * (1 - abs(random.gauss(0, intra_vol * 0.5)))
        open_p = max(open_p, 0.000001)
        low_p = max(low_p, 0.000001)
        volume = profile['volume_base'] * (0.5 + random.random())
        market_cap = close_p * SUPPLY[symbol]

        series.append({
            'date': today_str,
            'open': round(open_p, 6),
            'high': round(high_p, 6),
            'low': round(low_p, 6),
            'close': round(close_p, 6),
            'volume': round(volume, 2),
            'market_cap': round(market_cap, 2),
        })
        data[symbol] = series

    _atomic_write_json(data_file, data)
    logger.info('Live tick update complete.')


def load_data(data_file: str) -> dict:
    """Load and validate the crypto data JSON."""
    if not os.path.exists(data_file):
        raise FileNotFoundError(f'Data file not found: {data_file}')
    with open(data_file, 'r') as f:
        data = json.load(f)
    # Basic schema validation
    if not isinstance(data, dict):
        raise ValueError('Data root must be a dict keyed by coin symbol.')
    for symbol, series in data.items():
        if not isinstance(series, list):
            raise ValueError(f'Data for {symbol} must be a list of records.')
    return data


def get_coin_data(data_file: str, symbol: str) -> list[dict]:
    """Return OHLCV series for a single coin."""
    data = load_data(data_file)
    return data.get(symbol.upper(), [])


def _atomic_write_json(filepath: str, data: dict) -> None:
    """Write JSON atomically: write to temp file, then rename."""
    dir_name = os.path.dirname(filepath)
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, separators=(',', ':'))
        # On Windows, need to remove target first
        if os.path.exists(filepath):
            os.replace(tmp_path, filepath)
        else:
            os.rename(tmp_path, filepath)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
