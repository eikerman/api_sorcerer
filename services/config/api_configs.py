from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class ApiClientConfig:
    provider_id: str
    is_enabled: bool
    api_key: str
    base_url: str
    rate_limit: Optional[int] = None
    timeout: Optional[int] = 30
    additional_params: Optional[Dict[str, Any]] = None


class ConfigManager:
    def __init__(self, config_file_path: str):
        self._config_file_path = config_file_path
        self._configs = self._load_configs()

    def get_api_config(self, provider_id: str) -> Optional[ApiClientConfig]:
        config_data = self._configs.get(provider_id)
        if not config_data:
            return None

        return ApiClientConfig(
            provider_id=provider_id,
            is_enabled=config_data.get('enabled', False),
            api_key=config_data.get('api_key', ''),
            base_url=config_data.get('base_url', ''),
            rate_limit=config_data.get('rate_limit'),
            timeout=config_data.get('timeout', 30),
            additional_params=config_data.get('additional_params', {})
        )

    def enable_provider(self, provider_id: str):
        if provider_id in self._configs:
            self._configs[provider_id]['enabled'] = True
            self._save_configs()

    def disable_provider(self, provider_id: str):
        if provider_id in self._configs:
            self._configs[provider_id]['enabled'] = False
            self._save_configs()