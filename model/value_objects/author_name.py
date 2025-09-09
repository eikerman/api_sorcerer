import re
from dataclasses import dataclass

@dataclass(frozen=True)
class AuthorName:
    """Value object representing an author's name."""
    value: str

    def __post_init__(self):
        if not self.value:
            # Allow empty author names (some articles don't have authors)
            object.__setattr__(self, 'value', "")
            return

        # Clean and validate author name
        cleaned = self._clean_name(self.value)
        if len(cleaned) > 100:
            raise ValueError("Author name cannot exceed 100 characters")

        object.__setattr__(self, 'value', cleaned)

    @staticmethod
    def _clean_name(name: str) -> str:
        """Clean author name by removing excessive whitespace and normalizing."""
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', name.strip())

        # Remove common prefixes that might come from scraping
        prefixes_to_remove = ['by ', 'By ', 'BY ', 'Author: ', 'Written by ']
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()

        return cleaned

    @property
    def is_empty(self) -> bool:
        """Check if author name is empty."""
        return len(self.value.strip()) == 0

    @property
    def first_name(self) -> str:
        """Extract first name (rough approximation)."""
        if self.is_empty:
            return ""
        parts = self.value.split()
        return parts[0] if parts else ""

    @property
    def last_name(self) -> str:
        """Extract last name (rough approximation)."""
        if self.is_empty:
            return ""
        parts = self.value.split()
        return parts[-1] if len(parts) > 1 else ""

    def initials(self) -> str:
        """Get author initials."""
        if self.is_empty:
            return ""
        parts = self.value.split()
        return ''.join([part[0].upper() for part in parts if part])

    def __str__(self) -> str:
        return self.value if self.value else "Unknown Author"

    def __bool__(self) -> bool:
        return not self.is_empty