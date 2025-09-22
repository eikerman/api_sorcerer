
# infrastructure/config/rate_limits.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class RateLimitType(Enum):
    REQUESTS_PER_SECOND = "requests_per_second"
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    REQUESTS_PER_DAY = "requests_per_day"
    REQUESTS_PER_MONTH = "requests_per_month"

@dataclass
class RateLimit:
    """Represents a single rate limit constraint."""
    limit_type: RateLimitType
    max_requests: int

    def __str__(self) -> str:
        return f"{self.max_requests}/{self.limit_type.value.replace('_', ' ')}"

@dataclass
class ApiRateLimits:
    """Complete rate limiting configuration for an API."""

    # Short-term limits (burst protection)
    requests_per_second: Optional[int] = None
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None

    # Long-term limits (quota management)
    requests_per_day: Optional[int] = None
    requests_per_month: Optional[int] = None

    # Concurrent request limits
    max_concurrent_requests: Optional[int] = None

    def get_all_limits(self) -> list[RateLimit]:
        """Get all configured rate limits."""
        limits = []

        if self.requests_per_second:
            limits.append(RateLimit(RateLimitType.REQUESTS_PER_SECOND, self.requests_per_second))
        if self.requests_per_minute:
            limits.append(RateLimit(RateLimitType.REQUESTS_PER_MINUTE, self.requests_per_minute))
        if self.requests_per_hour:
            limits.append(RateLimit(RateLimitType.REQUESTS_PER_HOUR, self.requests_per_hour))
        if self.requests_per_day:
            limits.append(RateLimit(RateLimitType.REQUESTS_PER_DAY, self.requests_per_day))
        if self.requests_per_month:
            limits.append(RateLimit(RateLimitType.REQUESTS_PER_MONTH, self.requests_per_month))

        return limits

    def get_most_restrictive_per_hour(self) -> Optional[int]:
        """Calculate the most restrictive hourly limit across all constraints."""
        hourly_limits = []

        if self.requests_per_second:
            hourly_limits.append(self.requests_per_second * 3600)
        if self.requests_per_minute:
            hourly_limits.append(self.requests_per_minute * 60)
        if self.requests_per_hour:
            hourly_limits.append(self.requests_per_hour)
        if self.requests_per_day:
            hourly_limits.append(self.requests_per_day // 24)

        return min(hourly_limits) if hourly_limits else None