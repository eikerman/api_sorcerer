# API Sorcerer

A production-ready news article aggregation system that fetches articles from multiple news APIs, handles rate limiting, and stores deduplicated content in PostgreSQL.

## Features

- **Multi-API Support** - Extensible architecture for integrating multiple news APIs
- **Intelligent Rate Limiting** - Per-second, daily, and monthly rate limits with automatic pacing
- **Automatic Pagination** - Fetches all available articles across paginated responses
- **Deduplication** - URL-based deduplication prevents storing duplicate articles
- **Time Synchronization** - Reliable time service syncs with web servers for accurate timestamps
- **Retry Logic** - Automatic retry with exponential backoff for failed requests
- **Usage Tracking** - Persistent usage statistics across application restarts
- **Async/Await** - Fully asynchronous for optimal performance

## Architecture

```
api_sorcerer/
├── configs/
│   ├── api_config.py          # API configuration dataclass
│   └── config.yaml            # API provider settings
├── model/
│   └── article.py             # Article domain model
├── repository/
│   └── article_repository.py  # PostgreSQL data access layer
├── services/
│   ├── base/
│   │   ├── base_api_client.py     # Base class for API clients
│   │   ├── base_mapper.py         # Base mapper interface
│   │   ├── rate_limiter.py        # Rate limiting logic
│   │   └── time_service.py        # Time synchronization service
│   ├── clients/
│   │   └── news_api/
│   │       ├── client.py          # NewsAPI implementation
│   │       └── mapper.py          # NewsAPI response mapper
│   ├── article_service.py     # Main service orchestrator
│   └── client_factory.py      # Factory for creating API clients
├── tests/
│   ├── conftest.py
│   ├── test_api_config.py
│   ├── test_client_factory.py
│   ├── test_mapper.py
│   └── test_rate_limiter.py
├── main.py                    # Application entry point
└── requirements.txt
```

## Prerequisites

- Python 3.10+
- PostgreSQL 12+
- NewsAPI.org API key (get one at https://newsapi.org/)

## Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd news-aggregator
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up PostgreSQL database**
```bash
createdb newsdb
```

5. **Configure environment variables**
```bash
# Create .env file
cat > .env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=newsdb
DB_USER=your_user
DB_PASSWORD=your_password
CONFIG_PATH=configs/config.yaml
NEWSAPI_API_KEY=your_newsapi_key_here
EOF
```

6. **Configure API settings**

Edit `configs/config.yaml`:
```yaml
apis:
  newsapi:
    enabled: true
    api_key: "${NEWSAPI_API_KEY}"
    base_url: "https://newsapi.org/v2"
    rate_limits:
      requests_per_second: 5
      requests_per_day: 100
      requests_per_month: 2000
    timeout: 30
    max_total_requests: 5000
    hard_stop_date: "2025-12-31"
```

## Usage

### Basic Usage

```bash
# Load environment variables
export $(cat .env | xargs)

# Run the aggregator
python main.py
```

### Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=services --cov=configs --cov=model --cov-report=html

# Run specific test file
pytest tests/test_rate_limiter.py -v
```

## Configuration

### API Configuration Options

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Whether this API is active |
| `api_key` | string | API key (supports env vars with `${VAR}` syntax) |
| `base_url` | string | Base URL for the API |
| `timeout` | integer | Request timeout in seconds |
| `requests_per_second` | integer | Max requests per second (burst limit) |
| `requests_per_day` | integer | Max requests per day |
| `requests_per_month` | integer | Max requests per month |
| `max_total_requests` | integer | Lifetime request limit |
| `hard_stop_date` | string | Date to stop using this API (YYYY-MM-DD) |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | localhost | PostgreSQL host |
| `DB_PORT` | 5432 | PostgreSQL port |
| `DB_NAME` | newsdb | Database name |
| `DB_USER` | user | Database user |
| `DB_PASSWORD` | password | Database password |
| `CONFIG_PATH` | configs/config.yaml | Path to config file |

## Adding New API Providers

1. **Create client implementation**
```python
# services/clients/your_api/client.py
from services.base.base_api_client import BaseNewsApiClient

class YourApiClient(BaseNewsApiClient):
    @property
    def provider_id(self) -> str:
        return "your_api"
    
    async def build_request_url(self, query: str, from_date: Optional[datetime]) -> str:
        # Build your API URL
        pass
```

2. **Create response mapper**
```python
# services/clients/your_api/mapper.py
from services.base.base_mapper import BaseMapper

class YourApiMapper(BaseMapper):
    def get_items_from_response(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Extract articles from response
        pass
    
    def map_to_article(self, raw_data: Dict[str, Any], provider: str) -> Optional[Article]:
        # Map to Article model
        pass
```

3. **Register in factory**
```python
# services/client_factory.py
CLIENT_REGISTRY = {
    'newsapi': (NewsApiClient, NewsApiMapper),
    'your_api': (YourApiClient, YourApiMapper),  # Add this
}
```

4. **Add to config.yaml**
```yaml
apis:
  your_api:
    enabled: true
    api_key: "${YOUR_API_KEY}"
    base_url: "https://api.example.com"
    # ... other settings
```

## Rate Limiting

The system implements sophisticated rate limiting:

- **Burst Limiting**: Prevents exceeding per-second limits
- **Daily Pacing**: Distributes monthly quota evenly across days
- **Persistent Tracking**: Usage data survives restarts
- **Automatic Reset**: Daily/monthly counters reset automatically
- **Hard Stops**: Enforces total request limits and expiration dates

Usage data is stored in `./usage_data/{provider}_usage.json`

## Database Schema

```sql
CREATE TABLE articles (
    url_hash VARCHAR(32) PRIMARY KEY,
    source_url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    published_at TIMESTAMP NOT NULL,
    provider VARCHAR(50) NOT NULL,
    content TEXT,
    summary TEXT,
    author TEXT,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX idx_source_url ON articles(source_url);
CREATE INDEX idx_published_at ON articles(published_at DESC);
CREATE INDEX idx_provider ON articles(provider);
```

## Logging

Logs are written to both console and `news_aggregator.log`:

- **INFO**: Normal operations, statistics
- **WARNING**: Rate limits, retries
- **ERROR**: Failures, errors
- **CRITICAL**: Fatal errors

## Troubleshooting

### "No module named 'services'"
Ensure `tests/conftest.py` exists and adds the project root to Python path.

### Rate limit errors
Check `usage_data/` directory for usage files. Delete to reset counters (testing only).

### Database connection errors
Verify PostgreSQL is running and credentials are correct:
```bash
psql -h localhost -U your_user -d newsdb
```

### Time service sync failures
The system will fall back to system time if web servers are unreachable.

## Performance Considerations

- Uses connection pooling for database efficiency
- Async HTTP requests for parallel API calls
- Batch article insertion with conflict handling
- Indexes on frequently queried columns

## Future Enhancements

- [ ] Full-text search with PostgreSQL tsvector
- [ ] Article categorization/tagging
- [ ] Webhook notifications for new articles
- [ ] Admin dashboard
- [ ] Article similarity detection
- [ ] Scheduled fetching with cron/celery
- [ ] Docker containerization
- [ ] CI/CD pipeline

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues, questions, or contributions, please open an issue on GitHub.