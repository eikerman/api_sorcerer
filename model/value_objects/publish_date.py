from datetime import datetime, timezone
from dataclasses import  dataclass

@dataclass(frozen=True)
class PublishedDate:
    """Simple value object for article publication dates."""
    value: datetime

    def __post_init__(self):
        if not isinstance(self.value, datetime):
            raise ValueError("PublishedDate must be a datetime object")

        # Ensure timezone awareness - convert naive datetime to UTC
        if self.value.tzinfo is None:
            utc_datetime = self.value.replace(tzinfo=timezone.utc)
            object.__setattr__(self, 'value', utc_datetime)

    @classmethod
    def now(cls) -> 'PublishedDate':
        """Create PublishedDate for current moment."""
        return cls(datetime.now(timezone.utc))

    @classmethod
    def from_iso_string(cls, iso_string: str) -> 'PublishedDate':
        """Create PublishedDate from ISO format string (common in APIs)."""
        try:
            # Handle 'Z' suffix (Zulu time = UTC)
            if iso_string.endswith('Z'):
                iso_string = iso_string[:-1] + '+00:00'

            dt = datetime.fromisoformat(iso_string)
            return cls(dt)
        except ValueError as e:
            raise ValueError(f"Invalid date format: {iso_string}") from e

    @classmethod
    def from_datetime(cls, dt: datetime) -> 'PublishedDate':
        """Create PublishedDate from datetime object."""
        return cls(dt)

    def to_iso_string(self) -> str:
        """Convert to ISO format string."""
        return self.value.isoformat()

    def is_recent(self, hours: int = 24) -> bool:
        """Check if published within the last N hours."""
        now = datetime.now(timezone.utc)
        time_diff = now - self.value
        return time_diff.total_seconds() < (hours * 3600)

    def days_ago(self) -> int:
        """Get number of days since publication."""
        now = datetime.now(timezone.utc)
        time_diff = now - self.value
        return time_diff.days

    def __str__(self) -> str:
        return self.value.strftime("%Y-%m-%d %H:%M:%S UTC")

    def __eq__(self, other) -> bool:
        if not isinstance(other, PublishedDate):
            return False
        return self.value == other.value

    def __lt__(self, other) -> bool:
        if not isinstance(other, PublishedDate):
            return NotImplemented
        return self.value < other.value

    def __hash__(self) -> int:
        return hash(self.value)