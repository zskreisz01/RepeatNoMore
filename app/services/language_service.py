"""Language service for multi-language support."""

from functools import lru_cache
from pathlib import Path
from typing import Optional
import re

from app.config import get_settings
from app.storage.models import Language
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Hungarian language markers for detection
HUNGARIAN_MARKERS = {
    # Common Hungarian words
    "a", "az", "és", "hogy", "nem", "van", "egy", "ez", "mi", "te",
    "ő", "én", "volt", "lesz", "lett", "csak", "már", "még", "is",
    "ha", "de", "vagy", "mert", "aki", "ami", "mint", "után", "előtt",
    "alatt", "fölött", "között", "mellett", "hogyan", "miért", "mikor",
    # Hungarian question words
    "hol", "honnan", "hová", "melyik", "mennyi", "milyen",
    # Common verbs
    "kell", "lehet", "tud", "akar", "kér", "szeretne", "segít"
}

# English language markers
ENGLISH_MARKERS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "can", "shall", "and", "or", "but",
    "if", "then", "else", "when", "where", "why", "how", "what", "which",
    "who", "whom", "this", "that", "these", "those", "i", "you", "he",
    "she", "it", "we", "they", "my", "your", "his", "her", "its", "our"
}


class LanguageService:
    """Service for multi-language support."""

    def __init__(self):
        """Initialize language service."""
        self.settings = get_settings()
        self._user_preferences: dict[str, Language] = {}
        self.default_language = Language.EN
        self.supported_languages = [Language.EN, Language.HU]
        logger.info("language_service_initialized")

    def get_docs_path(self, language: Language) -> Path:
        """
        Get the documentation path for a language.

        Args:
            language: The target language

        Returns:
            Path to language-specific documentation folder
        """
        base = Path(self.settings.docs_repo_path)
        return base / language.value

    def get_qa_file_path(self, language: Language) -> Path:
        """
        Get the Q&A file path for a language.

        Args:
            language: The target language

        Returns:
            Path to the Q&A file for the language
        """
        base = Path(self.settings.docs_repo_path).parent
        return base / "qa" / f"accepted_qa_{language.value}.md"

    def get_suggestions_file_path(self) -> Path:
        """
        Get the feature suggestions file path.

        Returns:
            Path to the suggested features file
        """
        base = Path(self.settings.docs_repo_path).parent
        return base / "suggestions" / "suggested_features.md"

    def get_drafts_file_path(self) -> Path:
        """
        Get the draft updates file path.

        Returns:
            Path to the draft updates file
        """
        base = Path(self.settings.docs_repo_path).parent
        return base / "drafts" / "draft_updates.md"

    def detect_language(self, text: str) -> Language:
        """
        Detect the language of a text using keyword matching.

        Args:
            text: The text to analyze

        Returns:
            Detected language (defaults to English if uncertain)
        """
        if not text or not text.strip():
            return self.default_language

        # Normalize and tokenize
        words = set(re.findall(r'\b\w+\b', text.lower()))

        # Count marker matches
        hu_count = len(words.intersection(HUNGARIAN_MARKERS))
        en_count = len(words.intersection(ENGLISH_MARKERS))

        # Calculate ratios
        total_words = len(words)
        if total_words == 0:
            return self.default_language

        hu_ratio = hu_count / total_words
        en_ratio = en_count / total_words

        # Hungarian detection threshold (more sensitive to Hungarian)
        if hu_ratio > 0.05 and hu_ratio > en_ratio:
            detected = Language.HU
        else:
            detected = Language.EN

        logger.debug(
            "language_detected",
            language=detected.value,
            hu_ratio=round(hu_ratio, 3),
            en_ratio=round(en_ratio, 3)
        )

        return detected

    def set_user_preference(self, user_id: str, language: Language) -> None:
        """
        Set user's language preference.

        Args:
            user_id: User identifier (email or platform-specific ID)
            language: Preferred language
        """
        self._user_preferences[user_id.lower()] = language
        logger.info(
            "user_language_preference_set",
            user_id=user_id,
            language=language.value
        )

    def get_user_preference(self, user_id: str) -> Language:
        """
        Get user's language preference.

        Args:
            user_id: User identifier

        Returns:
            User's preferred language or default
        """
        return self._user_preferences.get(
            user_id.lower(),
            self.default_language
        )

    def clear_user_preference(self, user_id: str) -> None:
        """
        Clear user's language preference.

        Args:
            user_id: User identifier
        """
        user_id_lower = user_id.lower()
        if user_id_lower in self._user_preferences:
            del self._user_preferences[user_id_lower]
            logger.info("user_language_preference_cleared", user_id=user_id)

    def parse_language(self, language_str: str) -> Optional[Language]:
        """
        Parse a language string into a Language enum.

        Args:
            language_str: Language string (e.g., "en", "hu", "english", "hungarian")

        Returns:
            Language enum or None if invalid
        """
        lang_lower = language_str.lower().strip()

        if lang_lower in ("en", "english", "eng"):
            return Language.EN
        elif lang_lower in ("hu", "hungarian", "magyar", "hun"):
            return Language.HU

        return None

    def is_supported(self, language: Language) -> bool:
        """
        Check if a language is supported.

        Args:
            language: Language to check

        Returns:
            True if language is supported
        """
        return language in self.supported_languages

    def get_language_name(self, language: Language) -> str:
        """
        Get the display name for a language.

        Args:
            language: Language enum

        Returns:
            Display name for the language
        """
        names = {
            Language.EN: "English",
            Language.HU: "Hungarian"
        }
        return names.get(language, language.value)


# Global instance
_language_service: Optional[LanguageService] = None


@lru_cache()
def get_language_service() -> LanguageService:
    """
    Get or create a global language service instance.

    Returns:
        LanguageService: The language service
    """
    global _language_service
    if _language_service is None:
        _language_service = LanguageService()
    return _language_service
