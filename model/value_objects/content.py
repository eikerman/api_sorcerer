from dataclasses import dataclass
import html
import re

@dataclass(frozen=True)
class Content:
    """Value object representing article content with cleaning and validation."""
    value: str

    def __post_init__(self):
        if not isinstance(self.value, str):
            raise ValueError("Content must be a string")

        # Clean and normalize content
        cleaned = self._clean_content(self.value)
        object.__setattr__(self, 'value', cleaned)

    @staticmethod
    def _clean_content(content: str) -> str:
        """Clean HTML entities, normalize whitespace, remove excessive newlines."""
        # Decode HTML entities
        cleaned = html.unescape(content)

        # Remove excessive whitespace and newlines
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)

        # Strip leading/trailing whitespace
        cleaned = cleaned.strip()

        return cleaned

    @property
    def word_count(self) -> int:
        """Count words in the content."""
        return len(self.value.split())

    @property
    def character_count(self) -> int:
        """Count characters in the content."""
        return len(self.value)

    def excerpt(self, max_length: int = 200) -> str:
        """Create an excerpt of the content."""
        if len(self.value) <= max_length:
            return self.value

        # Find last space before max_length to avoid cutting words
        truncated = self.value[:max_length]
        last_space = truncated.rfind(' ')

        if last_space > max_length * 0.8:  # Don't cut too short
            truncated = truncated[:last_space]

        return truncated + "..."

    def is_substantial(self, min_words: int = 50) -> bool:
        """Check if content is substantial enough."""
        return self.word_count >= min_words

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)