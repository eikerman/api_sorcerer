# infrastructure/api_clients/client_factory.py
from typing import Dict, List, Type
from services.api_clients.base.news_api_client import INewsApiClient
from services.api_clients.newsapi_org.newsapi_client import NewsApiClient
from services.api_clients.guardian_api.guardian_client import GuardianClient

class ApiClientRegistry:
    def __init__(self):
        self._clients: Dict[str, Type[INewsApiClient]] = {}
        self._register_default_clients()

    def _register_default_clients(self):
        self.register('newsapi.org', NewsApiClient)
        self.register('guardian', GuardianClient)
        # Add more as needed

    def register(self, provider_id: str, client_class: Type[INewsApiClient]):
        self._clients[provider_id] = client_class

    def unregister(self, provider_id: str):
        if provider_id in self._clients:
            del self._clients[provider_id]

    def get_enabled_clients(self, config_manager: 'ConfigManager') -> List[INewsApiClient]:
        enabled_clients = []
        for provider_id, client_class in self._clients.items():
            config = config_manager.get_api_config(provider_id)
            if config and config.is_enabled:
                mapper = config_manager.get_mapper(provider_id)
                client = client_class(config, mapper)
                enabled_clients.append(client)
        return enabled_clients