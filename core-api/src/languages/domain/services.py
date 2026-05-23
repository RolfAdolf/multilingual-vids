from __future__ import annotations

from languages.domain.types import LanguageItem
from languages.lang_mapping import list_zeroswot_catalog_extras
from languages.models import Language


class LanguageCatalogService:
    def list_available(self) -> list[LanguageItem]:
        items: list[LanguageItem] = []
        seen: set[str] = set()
        for lang in Language.objects.all().order_by("name_en"):
            if not (lang.supports_source_speech or lang.supports_source_text):
                continue
            if lang.api_code in seen:
                continue
            seen.add(lang.api_code)
            items.append(
                LanguageItem(
                    code=lang.api_code,
                    name_en=lang.name_en,
                    name_ru=lang.name_ru or lang.name_en,
                )
            )
        for api_code, name_en in list_zeroswot_catalog_extras():
            if api_code in seen:
                continue
            seen.add(api_code)
            items.append(
                LanguageItem(code=api_code, name_en=name_en, name_ru=name_en)
            )
        return sorted(items, key=lambda item: item.name_en)
