from __future__ import annotations

import json
from typing import Any

from faker import Faker as FactoryFaker
from rest_framework.response import Response


factory_faker = FactoryFaker(["en_US", "ru_RU"])


def random_object_key(video_id: str, *, ext: str = ".mp4") -> str:
    """S3 key matching uploads/{uuid}/source.ext layout."""
    return f"uploads/{video_id}/source{ext}"


def assert_status(response: Response, expected: int) -> dict[str, Any]:
    assert response.status_code == expected, (
        f"Expected HTTP {expected}, got {response.status_code}: {response.content!r}"
    )
    if not response.content:
        return {}
    return response.json()


def assert_json_contains(data: dict[str, Any], **expected: Any) -> None:
    for key, value in expected.items():
        assert key in data, f"Missing key {key!r} in {json.dumps(data, default=str)}"
        assert data[key] == value, f"{key}: expected {value!r}, got {data[key]!r}"
