"""
CryptoLens – Prediction & ML Engine
Linear Regression + Random Forest trained on historical JSON data.
Provides 7-day and 30-day forecasts with accuracy metrics.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

# In-memory model cache: { 'BTC_lr': model, 'BTC_rf': model, ... }
_model_cache = {}
_data_hash_cache = {}


def _build_features(series: list[dict]) -> pd.DataFrame:
    """Engineer features from raw OHLCV series."""
    df = pd.DataFrame(series)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    df['day_of_week'] = df['date'].dt.dayofweek
    df['day_of_year'] = df['date'].dt.dayofyear
    df['month'] = df['date'].dt.month

    # Lag features
    for lag in [1, 3, 7, 14, 30]:
        df[f'close_lag_{lag}'] = df['close'].shift(lag)

    # Rolling statistics
    for window in [7, 14, 30]:
        df[f'rolling_mean_{window}'] = df['close'].rolling(window).mean()
        df[f'rolling_std_{window}'] = df['close'].rolling(window).std()

    # Price change features
    df['price_change_1d'] = df['close'].pct_change(1)
    df['price_change_7d'] = df['close'].pct_change(7)
    df['volume_change'] = df['volume'].pct_change(1)

    # Target: next day close
    df['target'] = df['close'].shift(-1)
    df = df.dropna().reset_index(drop=True)
    return df


def _get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return the feature column names used for training."""
    exclude = {'date', 'target', 'open', 'high', 'low', 'close', 'volume', 'market_cap'}
    return [c for c in df.columns if c not in exclude]


def _train_models(series: list[dict], symbol: str):
    """Train Linear Regression and Random Forest on the coin's historical data."""
    df = _build_features(series)
    if len(df) < 100:
        logger.warning(f'{symbol}: Not enough data to train ({len(df)} rows)')
        return None, None, None

    feature_cols = _get_feature_columns(df)
    X = df[feature_cols].values
    y = df['target'].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    lr = LinearRegression()
    lr.fit(X_train, y_train)

    rf = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)

    # Cache
    _model_cache[f'{symbol}_lr'] = lr
    _model_cache[f'{symbol}_rf'] = rf
    _data_hash_cache[symbol] = len(series)

    # Metrics on test set
    lr_pred = lr.predict(X_test)
    rf_pred = rf.predict(X_test)

    metrics = {
        'linear_regression': {
            'r2': round(r2_score(y_test, lr_pred), 4),
            'mae': round(mean_absolute_error(y_test, lr_pred), 4),
        },
        'random_forest': {
            'r2': round(r2_score(y_test, rf_pred), 4),
            'mae': round(mean_absolute_error(y_test, rf_pred), 4),
        },
        'test_actual': y_test.tolist()[-60:],
        'test_pred_lr': lr_pred.tolist()[-60:],
        'test_pred_rf': rf_pred.tolist()[-60:],
        'test_dates': df['date'].iloc[-len(y_test):].dt.strftime('%Y-%m-%d').tolist()[-60:],
    }

    logger.info(f'{symbol} models trained – LR R²={metrics["linear_regression"]["r2"]}, '
                f'RF R²={metrics["random_forest"]["r2"]}')
    return lr, rf, metrics


def _ensure_models(series: list[dict], symbol: str):
    """Return cached models or train new ones."""
    cached_len = _data_hash_cache.get(symbol, 0)
    if cached_len == len(series) and f'{symbol}_lr' in _model_cache:
        return _model_cache[f'{symbol}_lr'], _model_cache[f'{symbol}_rf'], None
    lr, rf, metrics = _train_models(series, symbol)
    return lr, rf, metrics


def predict(series: list[dict], symbol: str, days: int = 7) -> dict:
    """
    Generate price forecast for `days` ahead.
    Returns forecast values, confidence intervals, and accuracy metrics.
    """
    if len(series) < 100:
        return {'error': f'Insufficient data for {symbol} ({len(series)} records).'}

    lr, rf, train_metrics = _ensure_models(series, symbol)
    if lr is None:
        return {'error': 'Model training failed.'}

    # If we didn't just train, recalculate metrics
    if train_metrics is None:
        _, _, train_metrics = _train_models(series, symbol)

    df = _build_features(series)
    feature_cols = _get_feature_columns(df)

    # Iterative forecasting
    forecast_lr = []
    forecast_rf = []
    last_row = df.iloc[-1:].copy()

    for i in range(days):
        X_pred = last_row[feature_cols].values
        pred_lr = float(lr.predict(X_pred)[0])
        pred_rf = float(rf.predict(X_pred)[0])
        forecast_lr.append(round(pred_lr, 6))
        forecast_rf.append(round(pred_rf, 6))

        # Shift the row forward for next prediction
        new_row = last_row.copy()
        for lag in [1, 3, 7, 14, 30]:
            col = f'close_lag_{lag}'
            if lag == 1:
                new_row[col] = pred_rf
            else:
                new_row[col] = last_row[col].values[0]
        new_row['price_change_1d'] = (pred_rf - last_row['close_lag_1'].values[0]) / max(last_row['close_lag_1'].values[0], 0.0001)
        last_row = new_row

    # Confidence intervals (±1 std of recent residuals)
    recent = df['target'].values[-60:]
    recent_pred = rf.predict(df[feature_cols].values[-60:])
    residual_std = float(np.std(recent - recent_pred))

    forecast_dates = pd.date_range(
        start=pd.to_datetime(series[-1]['date']) + pd.Timedelta(days=1),
        periods=days
    ).strftime('%Y-%m-%d').tolist()

    return {
        'symbol': symbol,
        'days': days,
        'forecast_dates': forecast_dates,
        'forecast_lr': forecast_lr,
        'forecast_rf': forecast_rf,
        'confidence_upper': [round(v + residual_std, 6) for v in forecast_rf],
        'confidence_lower': [round(max(v - residual_std, 0), 6) for v in forecast_rf],
        'metrics': train_metrics,
    }
