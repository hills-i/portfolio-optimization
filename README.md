# Portfolio Optimization Web Application

A modern web application for financial portfolio analysis and optimization using Modern Portfolio Theory. Built with Flask and interactive visualizations.

## Features

- **Portfolio Optimization**: Calculate optimal asset allocations using Modern Portfolio Theory
- **Monte Carlo Simulation**: Generate thousands of random portfolios to explore risk-return relationships
- **Efficient Frontier**: Visualize the risk-return optimization curve
- **Risk Analysis**: Correlation matrix and risk decomposition analysis
- **Interactive Charts**: Real-time visualization with Plotly.js
- **Real-time Validation**: Client-side and server-side input validation
- **Export Functionality**: Download analysis results and charts

## Technology Stack

- **Backend**: Flask 3.1.0, Python 3.11+
- **Data Processing**: pandas 2.3.0, numpy 2.3.0, scipy 1.16.0
- **Financial Data**: yfinance 0.2.65 (Yahoo Finance API)
- **Visualization**: plotly 6.2.0
- **Frontend**: Bootstrap 5.3.2, vanilla JavaScript
- **Database**: SQLite (session management)

## Quick Start

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd money
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python src/run.py
```

5. Open your browser and navigate to `http://localhost:5001`

## Usage

1. **Enter Stock Tickers**: Add 2-20 stock symbols (e.g., AAPL, MSFT, GOOGL)
2. **Select Date Range**: Choose analysis period (1-10 years)
3. **Configure Parameters**: Set simulation count and risk-free rate
4. **Analyze**: Run portfolio optimization analysis
5. **Explore Results**: View interactive charts and optimal portfolios
6. **Export**: Download results in various formats

## Project Structure

```
src/
├── app/
│   ├── __init__.py          # Flask application factory
│   ├── routes.py           # Main web routes
│   ├── api/                # REST API endpoints
│   │   ├── __init__.py     # Blueprint initialization
│   │   └── portfolio.py    # Portfolio analysis API
│   ├── models/             # Data models
│   ├── utils/              # Core business logic
│   │   ├── validator.py    # Input validation
│   │   ├── data_fetcher.py # Yahoo Finance data retrieval
│   │   ├── calculator.py   # Portfolio optimization calculations
│   │   └── visualizer.py   # Plotly chart generation
│   ├── static/             # Static assets (CSS, JS, images)
│   └── templates/          # Jinja2 templates
├── config.py               # Application configuration
├── run.py                  # Application entry point
└── *.json                  # Cache files
```

## API Endpoints

- `GET /` - Main application interface
- `POST /api/validate` - Input validation
- `POST /api/ticker/validate` - Ticker symbol validation
- `POST /api/analyze` - Portfolio analysis
- `POST /api/visualize` - Chart generation
- `POST /api/export` - Results export
- `GET /api/health` - Health check

## Configuration

### Environment Variables

**Required for Production:**
- `SECRET_KEY`: Flask secret key for session security (required in production)
- `DATABASE_URL`: SQLite database path (optional, defaults to `sqlite:///portfolio.db`)

**Optional:**
- `FLASK_ENV`: Set to 'development' or 'production' (defaults to 'development')

**Example:**
```bash
export SECRET_KEY="your-random-secret-key-here"
export DATABASE_URL="sqlite:///production.db"
export FLASK_ENV="production"
```

### Default Settings

- **Risk-free rate**: 0.5% (configurable)
- **Simulation count**: 10,000 (range: 1,000-50,000)
- **Analysis period**: 1-10 years
- **Supported assets**: 2-20 tickers

## Development

### Running in Development Mode

```bash
python src/run.py
```

The application runs with debug mode enabled and auto-reload on code changes.

### Adding New Features

1. **New Chart Types**: Extend `PortfolioVisualizer` class
2. **Analysis Parameters**: Update validation rules and configuration
3. **Data Sources**: Create new fetcher classes following existing patterns

## Security

- Input sanitization and validation
- CSRF protection
- Secure session management
- No persistent storage of user data

## Performance

- Vectorized operations with NumPy/pandas
- Session-based caching
- Progressive loading with progress indicators
- Efficient client-side DOM updates

## License

This project is licensed under the MIT License - see the LICENSE file for details.
