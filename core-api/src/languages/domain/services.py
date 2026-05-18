from __future__ import annotations

from languages.domain.types import LanguageItem
from translation_models.domain.repository import ModelLanguageRepository

DEFAULT_LANGUAGE_NAMES: dict[str, tuple[str, str]] = {
    "de": ("German", "Немецкий"),
    "en": ("English", "Английский"),
    "ru": ("Russian", "Русский"),
    "uk": ("Ukrainian", "Украинский"),
}


class LanguageCatalogService:
    def __init__(self, repository: ModelLanguageRepository | None = None):
        self._repository = repository or ModelLanguageRepository()

    def list_available(self) -> list[LanguageItem]:
        codes: set[str] = set()
        for row in self._repository.active_language_rows().values(
            "source_language_code",
            "target_language_code",
        ):
            codes.add(row["source_language_code"])
            codes.add(row["target_language_code"])

        items: list[LanguageItem] = []
        for code in sorted(codes):
            name_en, name_ru = DEFAULT_LANGUAGE_NAMES.get(code, ("", ""))
            items.append(LanguageItem(code=code, name_en=name_en, name_ru=name_ru))
        return items
