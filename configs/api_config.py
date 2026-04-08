from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class ApiConfig:
    """Configuration for an API client"""
    provider_id: str
    enabled: bool
    api_key: str
    base_url: str
    timeout: int = 30

    # Rate limits
    requests_per_second: Optional[int] = None
    requests_per_day: Optional[int] = None
    requests_per_month: Optional[int] = None

    # Safety limits
    max_total_requests: Optional[int] = None
    hard_stop_date: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if hard stop date has passed"""
        if not self.hard_stop_date:
            return False
        stop_date = datetime.strptime(self.hard_stop_date, "%Y-%m-%d").date()
        return datetime.now().date() > stop_date