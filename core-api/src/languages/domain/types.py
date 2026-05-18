from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageItem:
    code: str
    name_en: str
    name_ru: str
