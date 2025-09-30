import asyncio
import time
from collections import deque
from typing import Dict, Any
import calendar
import json
from pathlib import Path
from datetime import date
import logging
from services.base.time_service import today
logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter with persistent usage tracking"""

    def __init__(self, provider_id: str, config: 'ApiConfig'):
        self.provider_id = provider_id
        self.config = config

        # Burst limiting (per second)
        self._request_times = deque()

        # Usage tracking
        self.storage_dir = Path("./usage_data")
        self.storage_dir.mkdir(exist_ok=True)
        self.usage_file = self.storage_dir / f"{provider_id}_usage.json"
        self._usage_data = self._load_usage()

    def _load_usage(self) -> Dict[str, Any]:
        """Load or create usage data"""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)
                    self._reset_counters_if_needed(data)
                    return data
            except IOError as e:
                logging.warning(f'Cannot open usage file {self.usage_file}, this is only a problem if'
                                f'this file is expected to exist and it is not the first time running the system')


        return {
            "daily_count": 0,
            "monthly_count": 0,
            "total_count": 0,
            "last_daily_reset": date.today().isoformat(),
            "last_monthly_reset": date.today().strftime("%Y-%m")
        }

    @staticmethod
    def _reset_counters_if_needed(data: Dict[str, Any]):
        """Reset daily/monthly counters if date boundaries crossed"""
        current_day = date.today()
        current_month = today().strftime("%Y-%m")

        if data["last_daily_reset"] != today().isoformat():
            data["daily_count"] = 0
            data["last_daily_reset"] = today().isoformat()

        if data["last_monthly_reset"] != current_month:
            data["monthly_count"] = 0
            data["last_monthly_reset"] = current_month

    def _save_usage(self):
        """Persist usage data"""
        with open(self.usage_file, 'w') as f:
            json.dump(self._usage_data, f, indent=2)

    def _calculate_daily_budget_from_monthly(self) -> int:
        """Calculate daily budget to evenly distribute monthly quota"""
        if not self.config.requests_per_month:
            logger.error(f'{self.provider_id} request per month are set to 0. If this is an active provider, this'
                         f'should be a non-zero amount')
            return 0

        current_date = today()
        days_in_month = calendar.monthrange(current_date.year, current_date.month)[1]

        # Calculate remaining budget for the rest of the month
        remaining_monthly = self.config.requests_per_month - self._usage_data["monthly_count"]
        days_remaining = days_in_month - current_date.day + 1

        if days_remaining > 0:
            return max(0, remaining_monthly // days_remaining)

        return 0

    def _in_within_paced_limit(self) -> bool:

        daily_budget = self._calculate_daily_budget_from_monthly()

        current_daily_usage = self._usage_data['daily_count']

        if current_daily_usage >= daily_budget:
            return False

        return True

    async def check_and_wait(self) -> bool:
        """
        Check rate limits and wait if necessary.
        Returns False if request should not be made (hard limits reached).
        """
        # Check safety limits
        if self.config.is_expired():
            logger.info(f"{self.provider_id}: Hard stop date reached")
            return False

        if self.config.max_total_requests:
            if self._usage_data["total_count"] >= self.config.max_total_requests:
                logger.info(f"{self.provider_id}: Max total requests reached")
                return False

        # Check daily/monthly limits
        if self.config.requests_per_day:
            if self._usage_data["daily_count"] >= self.config.requests_per_day:
                logger.info(f"{self.provider_id}: Daily limit reached")
                return False

        if self.config.requests_per_month:
            if self._usage_data["monthly_count"] >= self.config.requests_per_month:
                logger.info(f"{self.provider_id}: Monthly limit reached")
                return False

        # Handle burst limiting (per second)
        if self.config.requests_per_second:
            await self._wait_for_burst_limit()

        return True

    async def _wait_for_burst_limit(self):
        """Handle per-second rate limiting"""
        if not self.config.requests_per_second:
            return

        now = time.time()

        # Remove requests older than 1 second
        while self._request_times and self._request_times[0] < now - 1.0:
            self._request_times.popleft()

        # If at limit, wait
        if len(self._request_times) >= self.config.requests_per_second:
            sleep_time = 1.0 - (now - self._request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    def record_request(self):
        """Record that a request was made"""
        self._request_times.append(time.time())
        self._usage_data["daily_count"] += 1
        self._usage_data["monthly_count"] += 1
        self._usage_data["total_count"] += 1
        self._save_usage()

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        stats = dict(self._usage_data)

        # Add remaining quotas
        if self.config.requests_per_day:
            stats["daily_remaining"] = self.config.requests_per_day - self._usage_data["daily_count"]

        if self.config.requests_per_month:
            stats["monthly_remaining"] = self.config.requests_per_month - self._usage_data["monthly_count"]

        if self.config.max_total_requests:
            stats["total_remaining"] = self.config.max_total_requests - self._usage_data["total_count"]

        return stats