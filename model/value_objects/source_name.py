from dataclasses import dataclass
import re

@dataclass(frozen=True)
class SourceName:
    """Value object representing a news source name."""
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Source name cannot be empty")

        # Normalize the source name
        normalized = self.value.strip()
        if len(normalized) < 2:
            raise ValueError("Source name must be at least 2 characters")
        if len(normalized) > 100:
            raise ValueError("Source name cannot exceed 100 characters")

        # Update the value with normalized version
        object.__setattr__(self, 'value', normalized)

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if not isinstance(other, SourceName):
            return False
        return self.value.lower() == other.value.lower()

    def __hash__(self) -> int:
        return hash(self.value.lower())