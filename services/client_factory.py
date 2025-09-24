from typing import Dict, Any, List, Optional
import yaml
import os
from configs.api_config import ApiConfig
from services.base.base_api_client import BaseNewsApiClient
from services.clients.news_api.client import NewsApiOrgClient
from services.clients.news_api.mapper import NewsApiMapper

class ApiClientFactory:
    """Factory for creating configured API clients with their mappers"""
    
    # Registry of client types and their mappers
    CLIENT_REGISTRY = {
        'newsapi': (NewsApiOrgClient, NewsApiMapper),
        # Add more as: 'guardian': (GuardianClient, GuardianMapper),
    }
    
    @staticmethod
    def create_from_config(config_path: str) -> List[BaseNewsApiClient]:
        """Create all enabled clients from config file"""
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        clients = []
        
        for provider_id, settings in config_data.get('apis', {}).items():
            if not settings.get('enabled', False):
                continue
            
            client = ApiClientFactory.create_client(provider_id, settings)
            if client:
                clients.append(client)
        
        return clients
    
    @staticmethod
    def create_client(provider_id: str, settings: Dict[str, Any]) -> Optional[BaseNewsApiClient]:
        """Create a single client with its mapper"""
        if provider_id not in ApiClientFactory.CLIENT_REGISTRY:
            print(f"Unknown provider: {provider_id}")
            return None
        
        client_class, mapper_class = ApiClientFactory.CLIENT_REGISTRY[provider_id]
        
        # Replace environment variables in api_key
        api_key = settings.get('api_key', '')
        if api_key.startswith('${') and api_key.endswith('}'):
            env_var = api_key[2:-1]
            api_key = os.environ.get(env_var, '')
        
        # Build config
        config = ApiConfig(
            provider_id=provider_id,
            enabled=settings.get('enabled', True),
            api_key=api_key,
            base_url=settings.get('base_url', ''),
            timeout=settings.get('timeout', 30),
            requests_per_second=settings.get('rate_limits', {}).get('requests_per_second'),
            requests_per_day=settings.get('rate_limits', {}).get('requests_per_day'),
            requests_per_month=settings.get('rate_limits', {}).get('requests_per_month'),
            max_total_requests=settings.get('max_total_requests'),
            hard_stop_date=settings.get('hard_stop_date')
        )
        
        # Create mapper and client
        mapper = mapper_class()
        return client_class(config, mapper)