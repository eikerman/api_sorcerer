from services.api_clients.usage_tracking import ApiUsageTracker
from services.config.api_configs import ApiClientConfig
from datetime import datetime, date
from typing import Optional, Dict, Any
import logging


class ApiSafetyChecker:
    """
    Checks API safety limits and determines if an API should be disabled.

    Handles:
    - Hard stop dates (trial expiration, etc.)
    - Maximum total request limits
    - Integration with usage tracking
    """

    def __init__(self, usage_tracker: ApiUsageTracker, config: ApiClientConfig):
        self.usage_tracker = usage_tracker
        self.config = config
        self.provider_id = config.provider_id
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{self.provider_id}")

    def is_api_safe_to_use(self) -> tuple[bool, Optional[str]]:
        """
        Check if API is safe to use based on safety limits.

        Returns:
            (is_safe, reason_if_not_safe)
        """
        # Check hard stop date
        if self.config.hard_stop_date:
            if self._is_past_hard_stop_date():
                reason = f"Hard stop date {self.config.hard_stop_date} has been reached"
                self.logger.warning(f"API {self.provider_id} disabled: {reason}")
                return False, reason

        # Check maximum total requests
        if self.config.max_total_requests:
            current_total = self.usage_tracker.get_total_usage()
            if current_total >= self.config.max_total_requests:
                reason = f"Maximum total requests ({self.config.max_total_requests}) reached. Current: {current_total}"
                self.logger.warning(f"API {self.provider_id} disabled: {reason}")
                return False, reason

        return True, None

    def _is_past_hard_stop_date(self) -> bool:
        """Check if current date is past the hard stop date."""
        try:
            stop_date = datetime.strptime(self.config.hard_stop_date, "%Y-%m-%d").date()
            return date.today() > stop_date
        except ValueError as e:
            self.logger.error(f"Invalid hard_stop_date format '{self.config.hard_stop_date}': {e}")
            return False  # Don't disable on invalid date format

    def get_safety_status(self) -> Dict[str, Any]:
        """Get detailed safety status information."""
        is_safe, reason = self.is_api_safe_to_use()

        status = {
            "provider_id": self.provider_id,
            "is_safe": is_safe,
            "reason": reason,
            "checks": {}
        }

        # Hard stop date info
        if self.config.hard_stop_date:
            try:
                stop_date = datetime.strptime(self.config.hard_stop_date, "%Y-%m-%d").date()
                days_until_stop = (stop_date - date.today()).days
                status["checks"]["hard_stop_date"] = {
                    "limit": self.config.hard_stop_date,
                    "days_remaining": days_until_stop,
                    "is_past": days_until_stop < 0
                }
            except ValueError:
                status["checks"]["hard_stop_date"] = {
                    "limit": self.config.hard_stop_date,
                    "error": "Invalid date format"
                }

        # Max requests info
        if self.config.max_total_requests:
            current_total = self.usage_tracker.get_total_usage()
            remaining = max(0, self.config.max_total_requests - current_total)

            status["checks"]["max_total_requests"] = {
                "limit": self.config.max_total_requests,
                "current": current_total,
                "remaining": remaining,
                "percentage_used": (current_total / self.config.max_total_requests) * 100
            }

        return status

    def get_warnings(self, warning_threshold_days: int = 7, warning_threshold_percent: float = 90.0) -> list[str]:
        """
        Get warning messages for approaching limits.

        Args:
            warning_threshold_days: Warn when hard stop date is within this many days
            warning_threshold_percent: Warn when request usage exceeds this percentage

        Returns:
            List of warning messages
        """
        warnings = []

        # Hard stop date warning
        if self.config.hard_stop_date:
            try:
                stop_date = datetime.strptime(self.config.hard_stop_date, "%Y-%m-%d").date()
                days_until_stop = (stop_date - date.today()).days

                if 0 <= days_until_stop <= warning_threshold_days:
                    warnings.append(
                        f"Hard stop date approaching: {days_until_stop} days until {self.config.hard_stop_date}"
                    )
            except ValueError:
                pass

        # Max requests warning
        if self.config.max_total_requests:
            current_total = self.usage_tracker.get_total_usage()
            percentage_used = (current_total / self.config.max_total_requests) * 100

            if percentage_used >= warning_threshold_percent:
                remaining = max(0, self.config.max_total_requests - current_total)
                warnings.append(
                    f"Request limit approaching: {percentage_used:.1f}% used ({remaining} requests remaining)"
                )

        return warnings