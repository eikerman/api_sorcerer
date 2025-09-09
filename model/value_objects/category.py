from dataclasses import dataclass
from enum import Enum
from typing import Set


class CategoryType(Enum):
    """Predefined news categories."""
    TECHNOLOGY = "technology"
    POLITICS = "politics"
    BUSINESS = "business"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    SCIENCE = "science"
    WORLD = "world"
    LOCAL = "local"
    OPINION = "opinion"

    @classmethod
    def from_string(cls, category_str: str) -> 'CategoryType':
        """Convert string to CategoryType with fuzzy matching."""
        category_lower = category_str.lower().strip()

        # Direct mapping
        for cat_type in cls:
            if cat_type.value == category_lower:
                return cat_type

        # Fuzzy mapping for common variations
        mapping = {
            'tech': cls.TECHNOLOGY,
            'it': cls.TECHNOLOGY,
            'computing': cls.TECHNOLOGY,
            'political': cls.POLITICS,
            'politics': cls.POLITICS,
            'govt': cls.POLITICS,
            'government': cls.POLITICS,
            'biz': cls.BUSINESS,
            'finance': cls.BUSINESS,
            'economy': cls.BUSINESS,
            'sport': cls.SPORTS,
            'athletics': cls.SPORTS,
            'celeb': cls.ENTERTAINMENT,
            'celebrity': cls.ENTERTAINMENT,
            'movies': cls.ENTERTAINMENT,
            'music': cls.ENTERTAINMENT,
            'medical': cls.HEALTH,
            'medicine': cls.HEALTH,
            'wellness': cls.HEALTH,
            'international': cls.WORLD,
            'global': cls.WORLD,
            'foreign': cls.WORLD,
            'editorial': cls.OPINION,
            'op-ed': cls.OPINION,
        }

        return mapping.get(category_lower, cls.WORLD)  # Default to WORLD'

@dataclass(frozen=True)
class Category:
    """Value object representing an article category."""
    category_type: CategoryType
    subcategory: str = ""

    def __post_init__(self):
        # Normalize subcategory
        if self.subcategory:
            normalized_sub = self.subcategory.strip().lower()
            if len(normalized_sub) > 50:
                raise ValueError("Subcategory cannot exceed 50 characters")
            object.__setattr__(self, 'subcategory', normalized_sub)

    @classmethod
    def from_string(cls, category_str: str, subcategory: str = "") -> 'Category':
        """Create Category from string representation."""
        category_type = CategoryType.from_string(category_str)
        return cls(category_type, subcategory)

    @property
    def display_name(self) -> str:
        """Get display-friendly name."""
        base_name = self.category_type.value.replace('_', ' ').title()
        if self.subcategory:
            return f"{base_name} - {self.subcategory.title()}"
        return base_name

    def __str__(self) -> str:
        return self.display_name

    def __eq__(self, other) -> bool:
        if not isinstance(other, Category):
            return False
        return (self.category_type == other.category_type and
                self.subcategory == other.subcategory)

    def __hash__(self) -> int:
        return hash((self.category_type, self.subcategory))