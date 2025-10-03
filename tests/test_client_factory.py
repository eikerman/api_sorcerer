import pytest
import tempfile
import os
from services.client_factory import ApiClientFactory
from services.clients.news_api.client import NewsApiClient
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture
def sample_config_file():
    """Create a temporary config file"""
    config_content = """
apis:
  newsapi:
    enabled: true
    api_key: "test_api_key_123"
    base_url: "https://newsapi.org/v2"
    rate_limits:
      requests_per_second: 5
      requests_per_day: 100
      requests_per_month: 2000
    timeout: 30
    max_total_requests: 5000
    hard_stop_date: "2025-12-31"

  disabled_api:
    enabled: false
    api_key: "should_not_be_loaded"
    base_url: "https://disabled.com"
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def env_var_config_file():
    """Create config file that uses environment variables"""
    config_content = """
apis:
  newsapi:
    enabled: true
    api_key: "${TEST_API_KEY}"
    base_url: "https://newsapi.org/v2"
    timeout: 30
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_path = f.name

    yield temp_path

    os.unlink(temp_path)


class TestApiClientFactory:
    """Tests for ApiClientFactory"""

    def test_create_from_config(self, sample_config_file):
        """Test creating clients from config file"""
        clients = ApiClientFactory.create_from_config(sample_config_file)

        # Should only create enabled clients
        assert len(clients) == 1
        assert isinstance(clients[0], NewsApiClient)
        assert clients[0].provider_id == "newsapi.org"

    def test_disabled_apis_not_created(self, sample_config_file):
        """Test that disabled APIs are not instantiated"""
        clients = ApiClientFactory.create_from_config(sample_config_file)

        # disabled_api should not be in the list
        provider_ids = [c.provider_id for c in clients]
        assert "disabled_api" not in provider_ids

    def test_config_values_loaded_correctly(self, sample_config_file):
        """Test that config values are properly loaded into client"""
        clients = ApiClientFactory.create_from_config(sample_config_file)
        client = clients[0]

        assert client._config.provider_id == "newsapi"
        assert client._config.api_key == "test_api_key_123"
        assert client._config.base_url == "https://newsapi.org/v2"
        assert client._config.timeout == 30
        assert client._config.requests_per_second == 5
        assert client._config.requests_per_day == 100
        assert client._config.requests_per_month == 2000
        assert client._config.max_total_requests == 5000
        assert client._config.hard_stop_date == "2025-12-31"

    def test_environment_variable_substitution(self, env_var_config_file):
        """Test that environment variables are substituted in API keys"""
        # Set environment variable
        os.environ['TEST_API_KEY'] = 'secret_key_from_env'

        try:
            clients = ApiClientFactory.create_from_config(env_var_config_file)
            assert len(clients) == 1
            assert clients[0]._config.api_key == 'secret_key_from_env'
        finally:
            # Cleanup
            if 'TEST_API_KEY' in os.environ:
                del os.environ['TEST_API_KEY']

    def test_missing_environment_variable(self, env_var_config_file):
        """Test handling of missing environment variable"""
        # Ensure env var doesn't exist
        if 'TEST_API_KEY' in os.environ:
            del os.environ['TEST_API_KEY']

        clients = ApiClientFactory.create_from_config(env_var_config_file)
        assert len(clients) == 1
        # Should default to empty string
        assert clients[0]._config.api_key == ''

    def test_unknown_provider(self):
        """Test handling of unknown provider type"""
        config_content = """
apis:
  unknown_provider:
    enabled: true
    api_key: "test_key"
    base_url: "https://unknown.com"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            clients = ApiClientFactory.create_from_config(temp_path)
            # Unknown providers should be skipped
            assert len(clients) == 0
        finally:
            os.unlink(temp_path)

    def test_create_client_directly(self):
        """Test creating a single client directly"""
        settings = {
            'enabled': True,
            'api_key': 'direct_test_key',
            'base_url': 'https://newsapi.org/v2',
            'timeout': 45,
            'rate_limits': {
                'requests_per_second': 3,
                'requests_per_day': 50
            }
        }

        client = ApiClientFactory.create_client('newsapi', settings)

        assert client is not None
        assert isinstance(client, NewsApiClient)
        assert client._config.api_key == 'direct_test_key'
        assert client._config.timeout == 45
        assert client._config.requests_per_second == 3

    def test_empty_config_file(self):
        """Test handling empty config file"""
        config_content = "apis: {}"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            clients = ApiClientFactory.create_from_config(temp_path)
            assert len(clients) == 0
        finally:
            os.unlink(temp_path)

    def test_mapper_attached_to_client(self, sample_config_file):
        """Test that mapper is properly attached to client"""
        clients = ApiClientFactory.create_from_config(sample_config_file)
        client = clients[0]

        # Client should have a mapper
        assert client._mapper is not None
        assert hasattr(client._mapper, 'map_to_articles')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])