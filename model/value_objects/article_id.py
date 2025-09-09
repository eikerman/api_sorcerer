# domain/value_objects/article_id.py
import uuid
from dataclasses import dataclass

@dataclass(frozen=True)
class ArticleId:
    """Simple value object for article identifiers."""
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("ArticleId cannot be empty")

        # Normalize whitespace
        normalized = self.value.strip()
        object.__setattr__(self, 'value', normalized)

    @classmethod
    def generate(cls) -> 'ArticleId':
        """Generate a new random ArticleId using UUID."""
        return cls(str(uuid.uuid4()))

    @classmethod
    def from_string(cls, value: str) -> 'ArticleId':
        """Create ArticleId from string."""
        return cls(value)

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if not isinstance(other, ArticleId):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)
