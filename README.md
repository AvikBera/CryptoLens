# CryptoLens v1.0.0

**Enterprise Cryptocurrency Analysis & Forecasting Dashboard**
*Developed by AVIK*

---

## Overview

CryptoLens is a full-stack Flask web application for cryptocurrency market analysis and price forecasting. It features a custom data generation engine (no third-party APIs), encrypted user authentication, interactive Plotly-based visualizations, and machine learning predictions using scikit-learn.

## Features

- **Custom Data Engine** – Simulated OHLCV + Market Cap data for 10 coins (BTC, ETH, BNB, SOL, XRP, ADA, DOGE, DOT, AVAX, MATIC) from 2009–present
- **Secure Authentication** – Signup/Login/Logout with encrypted JSON storage (Fernet), hashed passwords (PBKDF2), CSRF protection, session management
- **Interactive Dashboard** – Candlestick charts, Moving Averages (MA20/MA50), Volume bars, RSI, MACD, Correlation Matrix Heatmap, Risk Analysis, Trend Strength Gauge
- **ML Predictions** – 7-day and 30-day price forecasts using Linear Regression & Random Forest with accuracy metrics (R², MAE), confidence intervals
- **Data Export** – CSV download and PNG chart export
- **Live Simulation** – Background scheduler updates prices every 60 seconds
- **Responsive Design** – Enterprise dark theme with glassmorphism, smooth animations, Font Awesome icons

## Tech Stack

| Layer      | Technology                                          |
|------------|-----------------------------------------------------|
| Backend    | Python 3.10+, Flask, Flask-Login, Flask-WTF         |
| Frontend   | HTML5, CSS3, Bootstrap 5, JavaScript, Plotly.js      |
| ML         | scikit-learn (Linear Regression, Random Forest)      |
| Security   | Werkzeug (password hashing), cryptography (Fernet)   |
| Scheduler  | APScheduler                                          |
| Icons      | Font Awesome 6                                       |

## Project Structure

```
CryptoLens/
├── app.py                 # Flask application entry point
├── config.py              # Configuration
├── requirements.txt       # Python dependencies
├── README.md
├── data/                  # Auto-generated data files
│   ├── crypto_data.json
│   └── users.json (encrypted)
├── models/
│   ├── data_engine.py     # Crypto data generator
│   ├── predictor.py       # ML forecasting engine
│   └── user_model.py      # User authentication model
├── static/
│   ├── css/style.css      # Enterprise dark theme
│   ├── js/dashboard.js    # Client-side charts & logic
│   └── img/               # Logo & favicon
└── templates/
    ├── base.html          # Master layout
    ├── login.html
    ├── signup.html
    ├── dashboard.html
    ├── prediction.html
    ├── coin_detail.html
    ├── 404.html
    └── 500.html
```

## Setup & Installation

### Prerequisites

- Python 3.10 or higher
- pip

### Steps

```bash
# 1. Clone the repository
git clone <repo-url>
cd CryptoLens

# 2. Create and activate virtual environment (recommended)
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python app.py
```

### First Run

On first launch, CryptoLens will automatically:
1. Generate historical crypto data (~5800+ daily records per coin) – this may take 30-60 seconds
2. Create the `data/` directory and `crypto_data.json`
3. Start the background scheduler for live price updates

### Access the App

Open your browser and navigate to: **http://127.0.0.1:5000**

1. Click **"Create one"** on the login page to register
2. Log in with your credentials
3. Explore the dashboard, predictions, and individual coin pages

## Screenshots

*Login Page → Dashboard → Predictions → Coin Detail*

## License

This project is developed as a BCA major project by **AVIK**.

---

**CryptoLens – v1.0.0 – Developed by AVIK**
