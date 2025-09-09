from dataclasses import dataclass
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Url:
    """Simple value object for URLs."""
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("URL cannot be empty")

        # Basic validation
        url = self.value.strip()

        if not self._is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}")

        object.__setattr__(self, 'value', url)

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Basic URL validation."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except Exception as e:
            logger.info(f'Invalid URL: {url} -- {e}')
            return False

    @property
    def domain(self) -> str:
        """Get the domain from the URL."""
        return urlparse(self.value).netloc

    def is_secure(self) -> bool:
        """Check if URL uses HTTPS."""
        return self.value.startswith('https://')

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if not isinstance(other, Url):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)
