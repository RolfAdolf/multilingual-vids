from __future__ import annotations

from pathlib import Path


def _tag_sentence(text: str, target_lang: str) -> str:
    sentence = text.strip()
    tag = f"<2{target_lang}>"
    if sentence.startswith("<2"):
        return sentence
    return f"{tag} {sentence}"


class ZeroshotMT:
    """SavedModel ExportTranslator (без зависимости от vocabs в рантайме)."""

    def __init__(self, saved_model_path: Path):
        import tensorflow as tf
        import tensorflow_text  # noqa: F401

        self.path = saved_model_path.resolve()
        self._model = tf.saved_model.load(str(self.path))

    def translate(self, text: str, target_lang: str = "uk") -> str:
        import tensorflow as tf

        sentence = _tag_sentence(text, target_lang)
        return self._model(tf.constant(sentence)).numpy().decode("utf-8")


def load_saved_model(path: str) -> ZeroshotMT:
    return ZeroshotMT(Path(path))
