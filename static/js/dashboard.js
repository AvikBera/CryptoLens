/**
 * CryptoLens v1.0.0 – Dashboard JavaScript
 * Client-side chart rendering, indicator calculations, and interactivity.
 * Developed by AVIK
 */

// ── Plotly Dark Theme Layout ───────────────────────────────────────────────
const plotlyDarkLayout = {
    paper_bgcolor: '#1a1f2e',
    plot_bgcolor: '#1a1f2e',
    font: { color: '#94a3b8', family: 'Inter, sans-serif', size: 12 },
    xaxis: { gridcolor: '#1e293b', linecolor: '#1e293b', zerolinecolor: '#1e293b' },
    yaxis: { gridcolor: '#1e293b', linecolor: '#1e293b', zerolinecolor: '#1e293b' },
    margin: { l: 50, r: 20, t: 20, b: 40 },
    legend: { bgcolor: 'transparent', font: { color: '#94a3b8' } },
    hoverlabel: { bgcolor: '#222839', font: { color: '#e2e8f0' } }
};

const plotlyConfig = { responsive: true, displayModeBar: false };

// ── State ──────────────────────────────────────────────────────────────────
let currentCoin = '';
let currentData = [];
let timeRange = 365;

// ── Coin Selection ─────────────────────────────────────────────────────────
function selectCoin(symbol) {
    currentCoin = symbol;
    // Update card styles
    document.querySelectorAll('.coin-card').forEach(card => {
        card.classList.toggle('active', card.dataset.symbol === symbol);
    });
    loadCoinData(symbol);
}

function setTimeRange(days) {
    timeRange = days;
    document.querySelectorAll('.control-bar .btn-control').forEach(btn => {
        if (['btn-1y', 'btn-6m', 'btn-3m', 'btn-1m'].includes(btn.id)) {
            btn.classList.remove('active');
        }
    });
    const map = { 365: 'btn-1y', 180: 'btn-6m', 90: 'btn-3m', 30: 'btn-1m' };
    const el = document.getElementById(map[days]);
    if (el) el.classList.add('active');
    if (currentData.length) renderAllCharts(currentData);
}

// ── Data Loading ───────────────────────────────────────────────────────────
function loadCoinData(symbol) {
    const loading = document.getElementById('loading');
    if (loading) loading.style.display = 'flex';

    fetch(`/api/data/${symbol}`)
        .then(res => res.json())
        .then(json => {
            if (loading) loading.style.display = 'none';
            if (json.error) { console.error(json.error); return; }
            currentData = json.data;
            updateStats(json.data);
            renderAllCharts(json.data);
        })
        .catch(err => {
            if (loading) loading.style.display = 'none';
            console.error('Failed to load data:', err);
        });
}

function refreshData() {
    if (currentCoin) loadCoinData(currentCoin);
}

// ── Stats Update ───────────────────────────────────────────────────────────
function updateStats(data) {
    if (data.length < 2) return;
    const last = data[data.length - 1];
    const prev = data[data.length - 2];
    const change = ((last.close - prev.close) / prev.close) * 100;

    const priceEl = document.getElementById('stat-price');
    const changeEl = document.getElementById('stat-change');
    const mcapEl = document.getElementById('stat-mcap');
    const volEl = document.getElementById('stat-volatility');

    if (priceEl) priceEl.textContent = '$' + formatNum(last.close);
    if (changeEl) {
        changeEl.textContent = change.toFixed(2) + '%';
        changeEl.style.color = change >= 0 ? '#10b981' : '#ef4444';
    }
    if (mcapEl) mcapEl.textContent = '$' + formatBig(last.market_cap);

    // Volatility: std dev of last 30 daily returns
    const returns = [];
    const slice = data.slice(-31);
    for (let i = 1; i < slice.length; i++) {
        returns.push((slice[i].close - slice[i - 1].close) / slice[i - 1].close);
    }
    const vol = stdDev(returns) * Math.sqrt(365) * 100;
    if (volEl) volEl.textContent = vol.toFixed(1) + '%';
}

// ── Render All Dashboard Charts ────────────────────────────────────────────
function renderAllCharts(data) {
    const sliced = data.slice(-timeRange);
    const dates = sliced.map(d => d.date);
    const closes = sliced.map(d => d.close);
    const opens = sliced.map(d => d.open);
    const highs = sliced.map(d => d.high);
    const lows = sliced.map(d => d.low);
    const volumes = sliced.map(d => d.volume);

    renderCandlestick(dates, opens, highs, lows, closes);
    renderMAChart(dates, closes);
    renderVolumeChart(dates, volumes, sliced);
    renderRSI(dates, closes);
    renderMACD(dates, closes);
    renderRiskPanel(sliced);
    renderTrendGauge(closes);
}

// ── Candlestick ────────────────────────────────────────────────────────────
function renderCandlestick(dates, opens, highs, lows, closes) {
    const el = document.getElementById('chart-candlestick');
    if (!el) return;
    Plotly.newPlot(el, [{
        x: dates, open: opens, high: highs, low: lows, close: closes,
        type: 'candlestick', name: currentCoin,
        increasing: { line: { color: '#10b981' } },
        decreasing: { line: { color: '#ef4444' } }
    }], {
        ...plotlyDarkLayout,
        xaxis: { ...plotlyDarkLayout.xaxis, rangeslider: { visible: false } }
    }, plotlyConfig);
}

// ── Moving Averages ────────────────────────────────────────────────────────
function renderMAChart(dates, closes) {
    const el = document.getElementById('chart-ma');
    if (!el) return;
    const ma20 = computeMA(closes, 20);
    const ma50 = computeMA(closes, 50);
    Plotly.newPlot(el, [
        { x: dates, y: closes, type: 'scatter', mode: 'lines', name: 'Price',
          line: { color: '#00d4aa', width: 2 } },
        { x: dates, y: ma20, type: 'scatter', mode: 'lines', name: 'MA20',
          line: { color: '#f59e0b', width: 1.5, dash: 'dot' } },
        { x: dates, y: ma50, type: 'scatter', mode: 'lines', name: 'MA50',
          line: { color: '#3b82f6', width: 1.5, dash: 'dash' } }
    ], plotlyDarkLayout, plotlyConfig);
}

// ── Volume ────────────────────────────────────────────────────────────────
function renderVolumeChart(dates, volumes, data) {
    const el = document.getElementById('chart-volume');
    if (!el) return;
    const colors = data.map((d, i) => i > 0 && d.close >= data[i - 1].close ? '#10b981' : '#ef4444');
    Plotly.newPlot(el, [{
        x: dates, y: volumes, type: 'bar',
        marker: { color: colors, opacity: 0.7 }, name: 'Volume'
    }], plotlyDarkLayout, plotlyConfig);
}

// ── RSI ───────────────────────────────────────────────────────────────────
function renderRSI(dates, closes) {
    const el = document.getElementById('chart-rsi');
    if (!el) return;
    const rsi = computeRSI(closes, 14);
    const rsiDates = dates.slice(14);
    Plotly.newPlot(el, [
        { x: rsiDates, y: rsi, type: 'scatter', mode: 'lines', name: 'RSI(14)',
          line: { color: '#a855f7', width: 2 } },
        { x: [rsiDates[0], rsiDates[rsiDates.length - 1]], y: [70, 70], mode: 'lines',
          line: { color: '#ef4444', width: 1, dash: 'dash' }, showlegend: false },
        { x: [rsiDates[0], rsiDates[rsiDates.length - 1]], y: [30, 30], mode: 'lines',
          line: { color: '#10b981', width: 1, dash: 'dash' }, showlegend: false }
    ], { ...plotlyDarkLayout, yaxis: { ...plotlyDarkLayout.yaxis, range: [0, 100] } }, plotlyConfig);
}

// ── MACD ──────────────────────────────────────────────────────────────────
function renderMACD(dates, closes) {
    const el = document.getElementById('chart-macd');
    if (!el) return;
    const macdData = computeMACD(closes);
    const n = macdData.macd.length;
    const macdDates = dates.slice(dates.length - n);
    Plotly.newPlot(el, [
        { x: macdDates, y: macdData.macd, type: 'scatter', mode: 'lines', name: 'MACD',
          line: { color: '#3b82f6', width: 2 } },
        { x: macdDates, y: macdData.signal, type: 'scatter', mode: 'lines', name: 'Signal',
          line: { color: '#f59e0b', width: 2 } },
        { x: macdDates, y: macdData.histogram, type: 'bar', name: 'Histogram',
          marker: { color: macdData.histogram.map(v => v >= 0 ? '#10b981' : '#ef4444'), opacity: 0.6 } }
    ], plotlyDarkLayout, plotlyConfig);
}

// ── Risk Panel ────────────────────────────────────────────────────────────
function renderRiskPanel(data) {
    const el = document.getElementById('risk-items');
    if (!el) return;

    const closes = data.map(d => d.close);
    const returns = [];
    for (let i = 1; i < closes.length; i++) {
        returns.push((closes[i] - closes[i - 1]) / closes[i - 1]);
    }

    const vol30 = stdDev(returns.slice(-30)) * Math.sqrt(365) * 100;
    const maxDrawdown = computeMaxDrawdown(closes);
    const sharpe = computeSharpe(returns.slice(-365));

    const items = [
        { label: 'Annualized Volatility', value: vol30.toFixed(1) + '%', risk: vol30 > 80 ? 'high' : vol30 > 40 ? 'medium' : 'low', pct: Math.min(vol30, 100) },
        { label: 'Max Drawdown', value: maxDrawdown.toFixed(1) + '%', risk: maxDrawdown > 50 ? 'high' : maxDrawdown > 25 ? 'medium' : 'low', pct: Math.min(maxDrawdown, 100) },
        { label: 'Sharpe Ratio', value: sharpe.toFixed(2), risk: sharpe < 0 ? 'high' : sharpe < 1 ? 'medium' : 'low', pct: Math.min(Math.abs(sharpe) * 33, 100) }
    ];

    el.innerHTML = items.map(item => `
        <div style="margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;">
                <span style="color:#94a3b8;">${item.label}</span>
                <span style="color:#e2e8f0;font-weight:600;font-family:'JetBrains Mono',monospace;">${item.value}</span>
            </div>
            <div class="risk-bar">
                <div class="risk-bar-fill risk-${item.risk}" style="width:${item.pct}%;"></div>
            </div>
        </div>
    `).join('');
}

// ── Trend Strength Gauge ──────────────────────────────────────────────────
function renderTrendGauge(closes) {
    const el = document.getElementById('chart-trend');
    if (!el) return;

    const ma20 = computeMA(closes, 20);
    const ma50 = computeMA(closes, 50);
    const last = closes[closes.length - 1];
    const lastMa20 = ma20[ma20.length - 1];
    const lastMa50 = ma50[ma50.length - 1];

    let strength = 50;
    if (lastMa20 && lastMa50) {
        if (last > lastMa20 && lastMa20 > lastMa50) strength = 85;
        else if (last > lastMa20) strength = 65;
        else if (last < lastMa20 && lastMa20 < lastMa50) strength = 15;
        else if (last < lastMa20) strength = 35;
    }

    Plotly.newPlot(el, [{
        type: 'indicator', mode: 'gauge+number',
        value: strength,
        gauge: {
            axis: { range: [0, 100], tickcolor: '#94a3b8' },
            bar: { color: strength > 60 ? '#10b981' : strength > 40 ? '#f59e0b' : '#ef4444' },
            bgcolor: '#151b2b',
            borderwidth: 0,
            steps: [
                { range: [0, 30], color: 'rgba(239,68,68,0.15)' },
                { range: [30, 70], color: 'rgba(245,158,11,0.15)' },
                { range: [70, 100], color: 'rgba(16,185,129,0.15)' }
            ]
        },
        number: { suffix: '%', font: { color: '#e2e8f0', size: 28 } }
    }], {
        ...plotlyDarkLayout,
        margin: { l: 30, r: 30, t: 10, b: 10 }
    }, plotlyConfig);
}

// ── Correlation Matrix ────────────────────────────────────────────────────
function loadCorrelation() {
    fetch('/api/correlation')
        .then(res => res.json())
        .then(json => {
            if (json.error) return;
            const el = document.getElementById('chart-correlation');
            if (!el) return;
            Plotly.newPlot(el, [{
                z: json.matrix,
                x: json.symbols,
                y: json.symbols,
                type: 'heatmap',
                colorscale: [
                    [0, '#ef4444'], [0.25, '#f59e0b'],
                    [0.5, '#1a1f2e'], [0.75, '#10b981'], [1, '#00d4aa']
                ],
                showscale: true,
                colorbar: { tickfont: { color: '#94a3b8' }, outlinewidth: 0 },
                hovertemplate: '%{x} vs %{y}: %{z:.3f}<extra></extra>'
            }], {
                ...plotlyDarkLayout,
                xaxis: { ...plotlyDarkLayout.xaxis, tickangle: -45 },
                yaxis: { ...plotlyDarkLayout.yaxis, autorange: 'reversed' }
            }, plotlyConfig);
        })
        .catch(console.error);
}

// ── Technical Indicator Calculations ───────────────────────────────────────

function computeMA(data, period) {
    const result = new Array(data.length).fill(null);
    for (let i = period - 1; i < data.length; i++) {
        let sum = 0;
        for (let j = i - period + 1; j <= i; j++) sum += data[j];
        result[i] = sum / period;
    }
    return result;
}

function computeEMA(data, period) {
    const k = 2 / (period + 1);
    const result = [data[0]];
    for (let i = 1; i < data.length; i++) {
        result.push(data[i] * k + result[i - 1] * (1 - k));
    }
    return result;
}

function computeRSI(closes, period) {
    const rsi = [];
    let avgGain = 0, avgLoss = 0;
    for (let i = 1; i <= period; i++) {
        const diff = closes[i] - closes[i - 1];
        if (diff >= 0) avgGain += diff; else avgLoss += Math.abs(diff);
    }
    avgGain /= period;
    avgLoss /= period;
    rsi.push(avgLoss === 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss)));

    for (let i = period + 1; i < closes.length; i++) {
        const diff = closes[i] - closes[i - 1];
        avgGain = (avgGain * (period - 1) + (diff >= 0 ? diff : 0)) / period;
        avgLoss = (avgLoss * (period - 1) + (diff < 0 ? Math.abs(diff) : 0)) / period;
        rsi.push(avgLoss === 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss)));
    }
    return rsi;
}

function computeMACD(closes) {
    const ema12 = computeEMA(closes, 12);
    const ema26 = computeEMA(closes, 26);
    const macd = ema12.map((v, i) => v - ema26[i]).slice(25);
    const signal = computeEMA(macd, 9);
    const histogram = macd.map((v, i) => v - signal[i]);
    return { macd, signal, histogram };
}

function computeMaxDrawdown(closes) {
    let peak = closes[0];
    let maxDD = 0;
    for (const price of closes) {
        if (price > peak) peak = price;
        const dd = ((peak - price) / peak) * 100;
        if (dd > maxDD) maxDD = dd;
    }
    return maxDD;
}

function computeSharpe(returns) {
    if (!returns.length) return 0;
    const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
    const sd = stdDev(returns);
    return sd === 0 ? 0 : (mean * 365) / (sd * Math.sqrt(365));
}

function stdDev(arr) {
    if (!arr.length) return 0;
    const mean = arr.reduce((a, b) => a + b, 0) / arr.length;
    const sq = arr.reduce((a, v) => a + (v - mean) ** 2, 0) / arr.length;
    return Math.sqrt(sq);
}

// ── Formatting Helpers ────────────────────────────────────────────────────

function formatNum(n) {
    if (n >= 1) return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return n.toFixed(6);
}

function formatBig(n) {
    if (n >= 1e12) return (n / 1e12).toFixed(2) + 'T';
    if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return n.toFixed(2);
}

// ── Export ─────────────────────────────────────────────────────────────────

function exportCSV() {
    if (!currentCoin) return;
    window.location.href = `/api/export/csv?coin=${currentCoin}`;
}

function exportPNG() {
    const el = document.getElementById('chart-candlestick');
    if (el) {
        Plotly.downloadImage(el, { format: 'png', width: 1400, height: 600, filename: `${currentCoin}_chart` });
    }
}
