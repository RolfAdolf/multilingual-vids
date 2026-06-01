import uuid

import factory

from tests.factories.translation_models import TranslationModelFactory
from tests.utils import random_object_key
from video.models import Video, VideoStatus


class VideoFactory(factory.django.DjangoModelFactory):
    id = factory.LazyFunction(uuid.uuid4)
    original_filename = "clip.mp4"
    model = factory.SubFactory(TranslationModelFactory)
    source_language_code = "en"
    target_language_code = "de"
    status = VideoStatus.WAITING
    progress = 0
    input_object_key = factory.LazyAttribute(
        lambda o: random_object_key(str(o.id))
    )
    content_type = "video/mp4"
    file_size_bytes = 1_024_000

    class Meta:
        model = Video
