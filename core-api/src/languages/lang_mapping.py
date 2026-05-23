"""
Hardcoded API ↔ model language codes.

SeamlessM4T catalog lives in the Language table (seeded by migration 0003).
ZeroSwot / Zeroshot model codes and pair rules are defined here for runtime.
"""

from __future__ import annotations

import logging
from typing import TypedDict

from languages.models import Language

logger = logging.getLogger(__name__)

SEAMLESS_M4T = "seamless_m4t"
ZEROSWOT = "zeroswot"
ZEROSHOT = "zeroshot"


class UnknownLanguageCodeError(ValueError):
    pass


class ZeroshotPairNotSupportedError(ValueError):
    pass


class ZeroSwotLang(TypedDict):
    nllb_code: str
    catalog_api_code: str


class ZeroshotLang(TypedDict):
    name_en: str
    whisper_code: str | None
    mt_tag: str | None
    tts_voice: str | None


# api_code -> nllb_code, catalog_api_code (for Language lookup fallback)
ZEROSWOT_BY_API: dict[str, ZeroSwotLang] = {
    "en": {"nllb_code": "eng_Latn", "catalog_api_code": "en"},
    "ar": {"nllb_code": "arb_Arab", "catalog_api_code": "ar"},
    "ca": {"nllb_code": "cat_Latn", "catalog_api_code": "ca"},
    "cy": {"nllb_code": "cym_Latn", "catalog_api_code": "cy"},
    "de": {"nllb_code": "deu_Latn", "catalog_api_code": "de"},
    "et": {"nllb_code": "est_Latn", "catalog_api_code": "et"},
    "fa": {"nllb_code": "pes_Arab", "catalog_api_code": "fa"},
    "id": {"nllb_code": "ind_Latn", "catalog_api_code": "id"},
    "ja": {"nllb_code": "jpn_Jpan", "catalog_api_code": "ja"},
    "lv": {"nllb_code": "lvs_Latn", "catalog_api_code": "lv"},
    "mn": {"nllb_code": "khk_Cyrl", "catalog_api_code": "mn"},
    "sl": {"nllb_code": "slv_Latn", "catalog_api_code": "sl"},
    "sv-se": {"nllb_code": "swe_Latn", "catalog_api_code": "sv"},
    "ta": {"nllb_code": "tam_Taml", "catalog_api_code": "ta"},
    "tr": {"nllb_code": "tur_Latn", "catalog_api_code": "tr"},
    "zh-cn": {"nllb_code": "zho_Hans", "catalog_api_code": "zh"},
}

ZEROSHOT_PAIRS: tuple[tuple[str, str], ...] = (
    ("de", "ru"),
    ("de", "en"),
    ("de", "uk"),
    ("en", "uk"),
)

ZEROSHOT_BY_API: dict[str, ZeroshotLang] = {
    "de": {"name_en": "German", "whisper_code": "de", "mt_tag": None, "tts_voice": None},
    "en": {
        "name_en": "English",
        "whisper_code": "en",
        "mt_tag": "en",
        "tts_voice": "en-US-JennyNeural",
    },
    "ru": {
        "name_en": "Russian",
        "whisper_code": None,
        "mt_tag": "ru",
        "tts_voice": "ru-RU-DmitryNeural",
    },
    "uk": {
        "name_en": "Ukrainian",
        "whisper_code": None,
        "mt_tag": "uk",
        "tts_voice": "uk-UA-OstapNeural",
    },
}


def normalize_zeroswot_api_code(code: str) -> str:
    return code.strip().lower()


def normalize_zeroshot_api_code(code: str) -> str:
    return code.strip().lower()


ZEROSHOT_PAIR_SET: set[tuple[str, str]] = {
    (normalize_zeroshot_api_code(s), normalize_zeroshot_api_code(t))
    for s, t in ZEROSHOT_PAIRS
}


def zeroswot_entry(api_code: str) -> ZeroSwotLang | None:
    return ZEROSWOT_BY_API.get(normalize_zeroswot_api_code(api_code))


def zeroshot_entry(api_code: str) -> ZeroshotLang | None:
    return ZEROSHOT_BY_API.get(normalize_zeroshot_api_code(api_code))


def zeroshot_pair_allowed(source_api: str, target_api: str) -> bool:
    return (
        normalize_zeroshot_api_code(source_api),
        normalize_zeroshot_api_code(target_api),
    ) in ZEROSHOT_PAIR_SET


def zeroshot_whisper_code(source_api: str) -> str:
    entry = zeroshot_entry(source_api)
    if not entry or not entry["whisper_code"]:
        raise KeyError(source_api)
    return entry["whisper_code"]


def zeroshot_mt_tag(target_api: str) -> str:
    entry = zeroshot_entry(target_api)
    if not entry or not entry["mt_tag"]:
        raise KeyError(target_api)
    return entry["mt_tag"]


def zeroshot_mt_tag_literal(target_api: str) -> str:
    return f"<2{zeroshot_mt_tag(target_api)}>"


def zeroshot_tts_voice(target_api: str) -> str:
    entry = zeroshot_entry(target_api)
    if not entry or not entry["tts_voice"]:
        raise KeyError(target_api)
    return entry["tts_voice"]


def nllb_lang_code(seamless_code: str, script: str) -> str:
    if "_" in seamless_code:
        base, script_part = seamless_code.split("_", 1)
        return f"{base}_{script_part}"
    if script:
        return f"{seamless_code}_{script}"
    return seamless_code


def zeroswot_model_lang_code(api_code: str) -> str:
    entry = zeroswot_entry(api_code)
    if not entry:
        raise UnknownLanguageCodeError(
            f"Language '{api_code}' is not supported by ZeroSwot"
        )
    return entry["nllb_code"]


def zeroshot_source_model_code(source_api: str) -> str:
    try:
        return zeroshot_whisper_code(source_api)
    except KeyError as exc:
        raise UnknownLanguageCodeError(
            f"Language '{source_api}' is not a Zeroshot source"
        ) from exc


def zeroshot_target_model_code(target_api: str) -> str:
    try:
        return zeroshot_mt_tag(target_api)
    except KeyError as exc:
        raise UnknownLanguageCodeError(
            f"Language '{target_api}' is not a Zeroshot MT target"
        ) from exc


def model_lang_code(
    model_slug: str,
    *,
    seamless_code: str,
    script: str,
    api_code: str,
    role: str = "any",
) -> str:
    if model_slug == SEAMLESS_M4T:
        return seamless_code
    if model_slug == ZEROSWOT:
        return zeroswot_model_lang_code(api_code)
    if model_slug == ZEROSHOT:
        if role == "source":
            return zeroshot_source_model_code(api_code)
        if role == "target":
            return zeroshot_target_model_code(api_code)
        raise UnknownLanguageCodeError(
            "Zeroshot requires role 'source' or 'target' for model_lang_code"
        )
    raise UnknownLanguageCodeError(f"Unknown model slug: {model_slug}")


def _language_for_api(api_code: str) -> Language:
    normalized = api_code.lower().strip()
    try:
        return Language.objects.get(api_code=normalized)
    except Language.DoesNotExist as exc:
        zw = zeroswot_entry(normalized)
        if zw:
            try:
                return Language.objects.get(api_code=zw["catalog_api_code"])
            except Language.DoesNotExist:
                pass
        if zeroshot_entry(normalized):
            raise UnknownLanguageCodeError(
                f"Language '{api_code}' is Zeroshot-only; use zeroshot model"
            ) from exc
        raise UnknownLanguageCodeError(
            f"Unknown API language code: {api_code}"
        ) from exc


def to_model_lang_code(model_slug: str, api_code: str) -> str:
    if model_slug == ZEROSWOT:
        code = zeroswot_model_lang_code(api_code)
        logger.debug("lang_mapping zeroswot api_code=%s -> %s", api_code, code)
        return code

    if model_slug == ZEROSHOT:
        raise UnknownLanguageCodeError(
            "Use pair_model_lang_codes() for zeroshot (source/target roles differ)"
        )

    lang = _language_for_api(api_code)
    code = model_lang_code(
        model_slug,
        seamless_code=lang.code,
        script=lang.script,
        api_code=lang.api_code,
    )
    logger.debug(
        "lang_mapping resolved model_slug=%s api_code=%s seamless=%s -> %s",
        model_slug,
        api_code,
        lang.code,
        code,
    )
    return code


def pair_model_lang_codes(
    model_slug: str,
    source_api: str,
    target_api: str,
) -> tuple[str, str]:
    if model_slug == ZEROSHOT:
        if not zeroshot_pair_allowed(source_api, target_api):
            raise ZeroshotPairNotSupportedError(
                f"Zeroshot does not support {source_api}->{target_api}. "
                f"Allowed: de->ru, de->en, de->uk, en->uk"
            )
        return (
            zeroshot_source_model_code(source_api),
            zeroshot_target_model_code(target_api),
        )
    return (
        to_model_lang_code(model_slug, source_api),
        to_model_lang_code(model_slug, target_api),
    )


def pair_from_video(video, model_slug: str | None = None) -> tuple[str, str]:
    slug = model_slug or video.model.slug
    return pair_model_lang_codes(
        slug,
        video.source_language_code,
        video.target_language_code,
    )


def is_zeroswot_supported(api_code: str) -> bool:
    return normalize_zeroswot_api_code(api_code) in ZEROSWOT_BY_API


def is_zeroshot_supported(source_api: str, target_api: str) -> bool:
    return zeroshot_pair_allowed(source_api, target_api)


def list_zeroswot_catalog_extras() -> tuple[tuple[str, str], ...]:
    """(api_code, name_en) for ZeroSwot-only API codes not in the seamless catalog."""
    return (
        ("sv-se", "Swedish"),
        ("zh-cn", "Chinese (Simplified)"),
    )


__all__ = [
    "UnknownLanguageCodeError",
    "ZeroshotPairNotSupportedError",
    "is_zeroshot_supported",
    "is_zeroswot_supported",
    "list_zeroswot_catalog_extras",
    "model_lang_code",
    "pair_from_video",
    "pair_model_lang_codes",
    "to_model_lang_code",
    "zeroshot_mt_tag",
    "zeroshot_mt_tag_literal",
    "zeroshot_source_model_code",
    "zeroshot_target_model_code",
    "zeroshot_tts_voice",
    "zeroswot_model_lang_code",
]
