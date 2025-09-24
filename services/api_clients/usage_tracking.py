import json
from datetime import datetime, date
from typing import Dict, Any
from pathlib import Path

class ApiUsageTracker:
    """
    Simple file-based usage_data tracker for API clients.

    Each API client gets its own JSON file to track daily/monthly usage_data.
    """

    def __init__(self, provider_id: str, storage_dir: str = "./usage_data"):
        self.provider_id = provider_id
        self.storage_dir = Path(storage_dir)
        self.file_path = self.storage_dir / f"{provider_id}_usage.json"

        self.storage_dir.mkdir(exist_ok=True)

        self._data = self._load_data()
        self._reset_counters_if_needed()

    def _load_data(self) -> Dict[str, Any]:
        """Load usage_data data from JSON file."""
        if not self.file_path.exists():
            return self._create_empty_data()

        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load usage_data data for {self.provider_id}: {e}")
            return self._create_empty_data()

    @staticmethod
    def _create_empty_data() -> Dict[str, Any]:
        """Create empty usage_data data structure."""
        today = date.today().isoformat()
        return {
            "daily_count": 0,
            "monthly_count": 0,
            "last_daily_reset": today,
            "last_monthly_reset": today[:7],  # YYYY-MM format
            "total_calls": 0,
            "created_at": datetime.now().isoformat()
        }

    def _reset_counters_if_needed(self):
        """Reset daily/monthly counters if we've crossed date boundaries."""
        today = date.today()
        current_month = today.strftime("%Y-%m")

        # Reset daily counter if it's a new day
        if self._data["last_daily_reset"] != today.isoformat():
            self._data["daily_count"] = 0
            self._data["last_daily_reset"] = today.isoformat()

        # Reset monthly counter if it's a new month
        if self._data["last_monthly_reset"] != current_month:
            self._data["monthly_count"] = 0
            self._data["last_monthly_reset"] = current_month

        # Save changes if any resets occurred
        self._save_data()

    def _save_data(self):
        """Save usage_data data to JSON file."""
        try:
            # Write to temp file first, then rename for atomic operation
            temp_path = self.file_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(self._data, f, indent=2)

            # Atomic rename
            temp_path.rename(self.file_path)

        except IOError as e:
            print(f"Warning: Could not save usage_data data for {self.provider_id}: {e}")

    def record_api_call(self):
        """Record a single API call."""
        self._data["daily_count"] += 1
        self._data["monthly_count"] += 1
        self._data["total_calls"] += 1
        self._data["last_call"] = datetime.now().isoformat()

        # Save to disk (you could batch this for performance if needed)
        self._save_data()

    def get_daily_usage(self) -> int:
        """Get current daily usage_data count."""
        self._reset_counters_if_needed()
        return self._data["daily_count"]

    def get_monthly_usage(self) -> int:
        """Get current monthly usage_data count."""
        self._reset_counters_if_needed()
        return self._data["monthly_count"]

    def get_total_usage(self) -> int:
        """Get total usage_data count (lifetime)."""
        return self._data["total_calls"]

    def can_make_request(self, daily_limit: int = None, monthly_limit: int = None) -> bool:
        """
        Check if we can make a request within the given limits.

        Args:
            daily_limit: Maximum requests per day (None = no limit)
            monthly_limit: Maximum requests per month (None = no limit)

        Returns:
            True if request is within limits
        """
        if daily_limit and self.get_daily_usage() >= daily_limit:
            return False

        if monthly_limit and self.get_monthly_usage() >= monthly_limit:
            return False

        return True

    def get_remaining_quota(self, daily_limit: int = None, monthly_limit: int = None) -> Dict[str, int]:
        """Get remaining quota for daily and monthly limits."""
        result = {}

        if daily_limit:
            result["daily_remaining"] = max(0, daily_limit - self.get_daily_usage())

        if monthly_limit:
            result["monthly_remaining"] = max(0, monthly_limit - self.get_monthly_usage())

        return result

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get complete usage_data summary."""
        return {
            "provider_id": self.provider_id,
            "daily_usage": self.get_daily_usage(),
            "monthly_usage": self.get_monthly_usage(),
            "total_usage": self.get_total_usage(),
            "last_daily_reset": self._data["last_daily_reset"],
            "last_monthly_reset": self._data["last_monthly_reset"],
            "last_call": self._data.get("last_call"),
            "created_at": self._data["created_at"]
        }

    def reset_usage(self, reset_daily: bool = False, reset_monthly: bool = False, reset_total: bool = False):
        """Manually reset usage_data counters (useful for testing or manual resets)."""
        if reset_daily:
            self._data["daily_count"] = 0
            self._data["last_daily_reset"] = date.today().isoformat()

        if reset_monthly:
            self._data["monthly_count"] = 0
            self._data["last_monthly_reset"] = date.today().strftime("%Y-%m")

        if reset_total:
            self._data["total_calls"] = 0

        self._save_data()