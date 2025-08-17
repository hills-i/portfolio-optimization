# Portfolio Optimization Web Application

A modern, responsive web application for financial portfolio analysis and optimization using Modern Portfolio Theory. Built with Flask and featuring interactive visualizations, multi-language support, and comprehensive risk analysis tools.

## ✨ Features

### 📊 **Core Analytics**
- **Portfolio Optimization**: Calculate optimal asset allocations using Modern Portfolio Theory
- **Monte Carlo Simulation**: Generate thousands of random portfolios (1,000-50,000 simulations)
- **Efficient Frontier**: Visualize the risk-return optimization curve
- **Risk Analysis**: Comprehensive correlation matrix and risk decomposition
- **Asset Statistics**: Individual stock performance metrics and risk measures

### 🎯 **Optimization Strategies**
- **Maximum Sharpe Ratio**: Find the portfolio with the best risk-adjusted returns
- **Minimum Variance**: Identify the lowest-risk portfolio combination
- **Target Return**: Calculate optimal weights for specific return objectives

### 🌐 **User Experience**
- **Interactive Charts**: Real-time visualization with Plotly.js
- **Multi-language Support**: English and Japanese localization
- **Real-time Validation**: Client-side and server-side input validation
- **Responsive Design**: Mobile-friendly Bootstrap interface
- **Export Functionality**: Download analysis results and charts

## 🛠 Technology Stack

- **Backend**: Flask 3.1.0, Python 3.11+
- **Data Processing**: pandas 2.3.0, numpy 2.3.0, scipy 1.16.0
- **Financial Data**: yfinance 0.2.65 (Yahoo Finance API)
- **Visualization**: plotly 6.2.0 for interactive charts
- **Frontend**: Bootstrap 5.3.2, vanilla JavaScript
- **Internationalization**: Flask-Babel for multi-language support
- **Database**: SQLite (session management)

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- pip package manager
- Internet connection (for fetching stock data)

### Installation

1. **Clone the repository:**

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
```bash
python src/run.py
```

5. **Open your browser:**
   - Navigate to `http://localhost:5002`
   - The application runs on port 5002 by default

### Docker (Optional)

```bash
# Build the Docker image
docker build -t portfolio-optimization .

# Run the container
docker run -p 5002:5002 portfolio-optimization
```

## 📖 Usage Guide

### Step-by-Step Analysis

1. **🎯 Enter Stock Tickers**
   - Add 2-20 stock symbols (e.g., AAPL, MSFT, GOOGL, TSLA)
   - Supports US and international stocks
   - Real-time ticker validation

2. **📅 Select Date Range**
   - Choose analysis period (1-10 years)
   - Minimum 1 year of historical data required
   - Automatically validates data availability

3. **⚙️ Configure Parameters**
   - **Simulation Count**: 1,000-50,000 Monte Carlo simulations
   - **Risk-free Rate**: Annual risk-free rate (default: 0.5%)
   - **Target Return**: Optional specific return objective

4. **🔄 Run Analysis**
   - Click "Analyze Portfolio" to start optimization
   - Progress indicator shows real-time status
   - Analysis typically completes in 10-30 seconds

5. **📊 Explore Results**
   - **Efficient Frontier**: Risk-return optimization curve
   - **Optimal Portfolios**: Max Sharpe, Min Variance, Target Return
   - **Correlation Matrix**: Asset correlation heatmap
   - **Monte Carlo**: Scatter plot of simulated portfolios
   - **Asset Statistics**: Individual performance metrics

6. **💾 Export Results**
   - Download charts as PNG/PDF
   - Export data as CSV/Excel
   - Save analysis summary

### Example Analysis

```
Tickers: AAPL, MSFT, GOOGL, AMZN
Date Range: 2022-01-01 to 2025-01-01
Simulation Count: 10,000
Risk-free Rate: 0.5%

Results:
- Max Sharpe Ratio: 1.45 (Return: 24.5%, Risk: 18.2%)
- Min Variance: Risk: 15.8% (Return: 18.3%)
- Correlation: AAPL-MSFT: 0.65, GOOGL-AMZN: 0.72
```

## 📁 Project Structure

```
portfolio-optimization/
├── src/                     # Source code
│   ├── app/
│   │   ├── __init__.py          # Flask application factory
│   │   ├── routes.py           # Main web routes
│   │   ├── api/                # REST API endpoints
│   │   │   ├── __init__.py     # Blueprint initialization
│   │   │   └── portfolio.py    # Portfolio analysis API
│   │   ├── models/             # Data models (minimal usage)
│   │   ├── utils/              # Core business logic
│   │   │   ├── validator.py    # Input validation & sanitization
│   │   │   ├── data_fetcher.py # Yahoo Finance data retrieval
│   │   │   ├── calculator.py   # Portfolio optimization algorithms
│   │   │   └── visualizer.py   # Plotly chart generation
│   │   ├── static/             # Frontend assets
│   │   │   ├── css/           # Stylesheets
│   │   │   ├── js/            # JavaScript modules
│   │   │   └── images/        # Image assets
│   │   ├── templates/         # Jinja2 HTML templates
│   │   └── translations/      # Multi-language support
│   │       ├── en/           # English translations
│   │       └── ja/           # Japanese translations
│   ├── config.py               # Application configuration
│   └── run.py                  # Application entry point
├── requirements.txt            # Python dependencies
├── babel.cfg                  # Babel configuration for i18n
├── LICENSE                    # MIT License
└── README.md                  # This file
```

## 🔌 API Endpoints

### Main Routes
- `GET /` - Main application interface (supports multi-language)
- `GET /<lang>/` - Language-specific interface

### Portfolio Analysis API
- `POST /api/validate` - Comprehensive input validation
- `POST /api/ticker/validate` - Real-time ticker symbol validation
- `POST /api/ticker/info` - Get ticker information and metadata
- `POST /api/analyze` - Main portfolio optimization analysis
- `POST /api/compare-simulations` - Compare different simulation parameters
- `POST /api/visualize` - Generate interactive charts and visualizations
- `POST /api/export` - Export analysis results in various formats
- `GET /api/health` - Application health check and status

### API Response Format
```json
{
  "success": true,
  "data": {
    "optimal_portfolios": {...},
    "efficient_frontier": {...},
    "monte_carlo_results": {...}
  },
  "message": "Analysis completed successfully",
  "timestamp": "2025-08-17T10:30:00Z"
}
```

## ⚙️ Configuration

### Environment Variables

**Production Required:**
- `SECRET_KEY`: Flask secret key for session security
- `FLASK_ENV`: Set to 'production' for production deployment

**Optional Configuration:**
- `DATABASE_URL`: SQLite database path (default: `sqlite:///portfolio.db`)

**Example Production Setup:**
```bash
export SECRET_KEY="your-randomly-generated-secret-key-here"
export DATABASE_URL="sqlite:///production.db"
export FLASK_ENV="production"
```

**Development Setup:**
```bash
# Development uses secure defaults
export FLASK_ENV="development"
```

### Application Settings

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| Risk-free Rate | 0.5% | 0-10% | Annual risk-free rate for Sharpe ratio calculations |
| Simulation Count | 10,000 | 1,000-50,000 | Monte Carlo simulation iterations |
| Analysis Period | 3 years | 1-10 years | Historical data timeframe |
| Asset Count | 2-20 | 2-20 | Number of supported tickers per analysis |
| Session Timeout | 1 hour | - | User session duration |
| Data Fetch Timeout | 30 seconds | - | Yahoo Finance API timeout |

## 🛠 Development

### Development Environment

```bash
# Clone and setup
cd portfolio-optimization
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run development server
python src/run.py
```

**Development Features:**
- 🔄 Auto-reload on code changes
- 🐛 Debug mode with detailed error pages
- 📝 Comprehensive logging to `app.log`
- 🌐 Multi-language hot-reload
- 🧪 Built-in testing utilities

### Adding New Features

| Component | Location | Purpose |
|-----------|----------|---------|
| **Chart Types** | `src/app/utils/visualizer.py` | Extend `PortfolioVisualizer` class |
| **Analysis Parameters** | `src/config.py` + `src/app/utils/validator.py` | Update validation rules |
| **Data Sources** | `src/app/utils/data_fetcher.py` | Create new fetcher classes |
| **API Endpoints** | `src/app/api/portfolio.py` | Add new analysis routes |
| **Frontend Features** | `src/app/static/js/` | Extend JavaScript modules |

### Testing

```bash
# Run basic health check
curl http://localhost:5002/api/health

# Test portfolio analysis
curl -X POST http://localhost:5002/api/validate \
  -H "Content-Type: application/json" \
  -d '{"tickers":["AAPL","MSFT"],"start_date":"2023-01-01","end_date":"2024-01-01"}'
```

## 🔒 Security & Privacy

### Security Features
- ✅ **Input Validation**: Comprehensive sanitization and validation
- ✅ **Session Security**: Secure session management with timeout
- ✅ **No Data Persistence**: No storage of user portfolio data
- ✅ **Environment Variables**: Secure configuration management
- ✅ **Error Handling**: Safe error messages without data leakage

### Privacy Protection
- 🔐 **No Personal Data**: Only processes public stock ticker symbols
- 🚫 **No Data Storage**: Analysis results are session-only
- 🛡️ **Secure Headers**: Standard security headers implemented
- 📝 **Audit Logs**: Comprehensive logging for security monitoring

## ⚡ Performance

### Optimization Features
- **Vectorized Operations**: NumPy/pandas for efficient calculations
- **Smart Caching**: Session-based result caching
- **Progressive Loading**: Real-time progress indicators
- **Lazy Loading**: On-demand chart rendering
- **Efficient DOM**: Minimal client-side updates

### Performance Metrics
- Analysis Time: 10-30 seconds (10,000 simulations)
- Memory Usage: ~100MB peak during analysis
- Concurrent Users: Supports multiple simultaneous analyses
- Chart Rendering: <2 seconds for interactive visualizations

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings for all functions
- Include type hints where applicable

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.