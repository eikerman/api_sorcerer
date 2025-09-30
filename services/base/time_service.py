# infrastructure/time_service/time_service.py
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
import logging


@dataclass
class TimeServer:
    """Configuration for a time server."""
    url: str
    name: str
    priority: int = 1  # Lower number = higher priority


class ReliableTimeService:
    """
    Service that maintains accurate time by syncing with multiple web servers.

    Uses HTTP Date headers from reliable servers to calibrate local time.
    Automatically falls back to backup servers if primary fails.
    """

    # Default reliable time servers (major services with accurate clocks)
    DEFAULT_TIME_SERVERS = [
        TimeServer("https://www.google.com", "Google", priority=1),
        TimeServer("https://www.cloudflare.com", "Cloudflare", priority=1),
        TimeServer("https://www.amazon.com", "Amazon", priority=2),
        TimeServer("https://www.microsoft.com", "Microsoft", priority=2),
        TimeServer("https://api.github.com", "GitHub", priority=3),
    ]

    def __init__(
            self,
            time_servers: Optional[List[TimeServer]] = None,
            sync_interval_minutes: int = 60,
            max_drift_seconds: int = 30
    ):
        """
        Initialize the time service.

        Args:
            time_servers: List of time servers to use (uses defaults if None)
            sync_interval_minutes: How often to sync with servers
            max_drift_seconds: Maximum allowed drift before forcing re-sync
        """
        self.time_servers = time_servers or self.DEFAULT_TIME_SERVERS
        self.sync_interval = timedelta(minutes=sync_interval_minutes)
        self.max_drift = timedelta(seconds=max_drift_seconds)

        # Time offset from system time
        self._time_offset: Optional[timedelta] = None
        self._last_sync: Optional[datetime] = None
        self._is_synced = False
        self._sync_task: Optional[asyncio.Task] = None

        # HTTP client
        self._client = httpx.AsyncClient(timeout=10.0)

        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize(self):
        """Initialize and perform first sync."""
        await self.sync_time()

        # Start background sync task
        self._sync_task = asyncio.create_task(self._background_sync())

        self.logger.info("ReliableTimeService initialized and synced")

    async def sync_time(self) -> bool:
        """
        Sync time with web servers.

        Returns:
            True if sync was successful
        """
        self.logger.info("Syncing time with web servers...")

        # Sort servers by priority
        sorted_servers = sorted(self.time_servers, key=lambda s: s.priority)

        # Try each server until successful
        for server in sorted_servers:
            try:
                server_time = await self._get_time_from_server(server)
                if server_time:
                    # Calculate offset from system time
                    system_time = datetime.now(timezone.utc)
                    self._time_offset = server_time - system_time
                    self._last_sync = system_time
                    self._is_synced = True

                    offset_seconds = self._time_offset.total_seconds()
                    self.logger.info(
                        f"Time synced with {server.name}: "
                        f"offset={offset_seconds:.2f}s"
                    )
                    return True

            except Exception as e:
                self.logger.warning(f"Failed to sync with {server.name}: {e}")
                continue

        self.logger.error("Failed to sync with any time server")
        return False

    async def _get_time_from_server(self, server: TimeServer) -> Optional[datetime]:
        """
        Get current time from a web server using HTTP Date header.

        Args:
            server: Time server configuration

        Returns:
            Current datetime from server, or None if failed
        """
        try:
            # Make HEAD request (faster than GET)
            response = await self._client.head(server.url, follow_redirects=True)

            # Extract Date header
            date_header = response.headers.get('Date')
            if not date_header:
                self.logger.warning(f"{server.name} response has no Date header")
                return None

            # Parse HTTP date format
            server_time = parsedate_to_datetime(date_header)

            # Ensure timezone awareness
            if server_time.tzinfo is None:
                server_time = server_time.replace(tzinfo=timezone.utc)
            else:
                server_time = server_time.astimezone(timezone.utc)

            return server_time

        except Exception as e:
            self.logger.debug(f"Error getting time from {server.name}: {e}")
            return None

    async def _background_sync(self):
        """Background task to periodically sync time."""
        while True:
            try:
                await asyncio.sleep(self.sync_interval.total_seconds())
                await self.sync_time()

            except asyncio.CancelledError:
                self.logger.info('Background sync task cancelled')
                raise

            except Exception as e:
                self.logger.error(f"Error in background sync: {e}")


    def now(self) -> datetime:
        """
        Get current datetime with calibrated time.

        Returns:
            Current datetime in UTC
        """
        system_time = datetime.now(timezone.utc)

        # If not synced yet, use system time
        if not self._is_synced or self._time_offset is None:
            self.logger.warning("Time not synced yet, using system time")
            return system_time

        # Check if we need to re-sync (drift detection)
        if self._last_sync:
            time_since_sync = system_time - self._last_sync
            if time_since_sync > self.sync_interval + self.max_drift:
                self.logger.warning("Time drift detected, triggering re-sync")
                # Trigger async re-sync without waiting (don't store reference)
                asyncio.create_task(self.sync_time())

        # Return calibrated time
        return system_time + self._time_offset

    def today(self) -> datetime.date:
        """Get current date with calibrated time."""
        return self.now().date()

    def get_sync_status(self) -> dict:
        """Get detailed sync status information."""
        system_time = datetime.now(timezone.utc)

        status = {
            "is_synced": self._is_synced,
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "offset_seconds": self._time_offset.total_seconds() if self._time_offset else None,
            "system_time": system_time.isoformat(),
            "calibrated_time": self.now().isoformat() if self._is_synced else None
        }

        if self._last_sync:
            time_since_sync = system_time - self._last_sync
            status["time_since_sync_seconds"] = time_since_sync.total_seconds()
            status["next_sync_in_seconds"] = max(
                0,
                (self.sync_interval - time_since_sync).total_seconds()
            )

        return status

    async def verify_sync(self) -> Tuple[bool, float]:
        """
        Verify current sync accuracy by checking against servers.

        Returns:
            (is_accurate, max_difference_seconds)
        """
        if not self._is_synced:
            return False, float('inf')

        current_calibrated = self.now()
        max_diff = 0.0
        successful_checks = 0

        for server in self.time_servers[:3]:  # Check top 3 servers
            try:
                server_time = await self._get_time_from_server(server)
                if server_time:
                    diff = abs((server_time - current_calibrated).total_seconds())
                    max_diff = max(max_diff, diff)
                    successful_checks += 1
            except Exception as E:
                self.logger.warning(f'Time Server call {server} unsuccessful. Calling next. {E}')
                continue

        if successful_checks == 0:
            return False, float('inf')

        # Consider accurate if within 5 seconds
        is_accurate = max_diff < 5.0
        return is_accurate, max_diff

    async def close(self):
        """Close the HTTP client and cancel background tasks."""
        # Cancel background sync task
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        # Close HTTP client
        await self._client.aclose()

        self.logger.info("ReliableTimeService closed")



# Global singleton instance
_time_service_instance: Optional[ReliableTimeService] = None


async def get_time_service() -> ReliableTimeService:
    """Get or create the global time service instance."""
    global _time_service_instance

    if _time_service_instance is None:
        _time_service_instance = ReliableTimeService()
        await _time_service_instance.initialize()

    return _time_service_instance


def now() -> datetime:
    """
    Convenience function to get current calibrated time.

    Note: Requires time service to be initialized first.
    """
    global _time_service_instance

    if _time_service_instance is None:
        logging.warning("Time service not initialized, using system time")
        return datetime.now(timezone.utc)

    return _time_service_instance.now()


def today() -> datetime.date:
    """
    Convenience function to get current calibrated date.

    Note: Requires time service to be initialized first.
    """
    global _time_service_instance

    if _time_service_instance is None:
        logging.warning("Time service not initialized, using system date")
        return datetime.now(timezone.utc).date()

    return _time_service_instance.today()

async def close_time_service():
    """Close the global time service instance."""
    global _time_service_instance

    if _time_service_instance is not None:
        await _time_service_instance.close()
        _time_service_instance = None