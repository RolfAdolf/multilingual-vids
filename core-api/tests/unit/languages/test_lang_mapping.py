import pytest

from languages.lang_mapping import (
    UnknownLanguageCodeError,
    ZeroshotPairNotSupportedError,
    is_zeroswot_supported,
    is_zeroshot_supported,
    pair_model_lang_codes,
    zeroswot_model_lang_code,
    zeroshot_mt_tag_literal,
)


@pytest.mark.parametrize(
    ("api_code", "nllb"),
    [
        ("en", "eng_Latn"),
        ("de", "deu_Latn"),
        ("zh-cn", "zho_Hans"),
        ("sv-se", "swe_Latn"),
    ],
)
def test_zeroswot_model_lang_code(api_code, nllb):
    assert zeroswot_model_lang_code(api_code) == nllb


def test_zeroswot_unknown_language_raises():
    with pytest.raises(UnknownLanguageCodeError):
        zeroswot_model_lang_code("xx")


@pytest.mark.parametrize("api_code", ["en", "de", "zh-cn", "SV-SE"])
def test_is_zeroswot_supported(api_code):
    assert is_zeroswot_supported(api_code)


def test_is_zeroswot_supported_false():
    assert not is_zeroswot_supported("xx")


@pytest.mark.parametrize(
    ("source", "target", "allowed"),
    [
        ("de", "uk", True),
        ("de", "en", True),
        ("en", "uk", True),
        ("de", "ru", True),
        ("en", "de", False),
        ("uk", "en", False),
    ],
)
def test_is_zeroshot_supported(source, target, allowed):
    assert is_zeroshot_supported(source, target) is allowed


def test_pair_model_lang_codes_zeroswot():
    src, tgt = pair_model_lang_codes("zeroswot", "en", "de")
    assert src == "eng_Latn"
    assert tgt == "deu_Latn"


def test_pair_model_lang_codes_zeroshot_ok():
    src, tgt = pair_model_lang_codes("zeroshot", "de", "uk")
    assert src == "de"
    assert tgt == "uk"


def test_pair_model_lang_codes_zeroshot_rejects_unsupported():
    with pytest.raises(ZeroshotPairNotSupportedError):
        pair_model_lang_codes("zeroshot", "en", "de")


def test_zeroshot_mt_tag_literal():
    assert zeroshot_mt_tag_literal("uk") == "<2uk>"
