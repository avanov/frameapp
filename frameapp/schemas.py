import json
from typing import Dict
import pathlib

from django.conf import settings


def json_schema(from_file: str) -> Dict:
    return json.loads(json_schema_str(from_file))


def json_schema_str(from_file: str) -> str:
    path = pathlib.Path(f'{settings.ROOT_PATH}/mobile_api/schemas/{from_file}')
    with path.open('r', encoding='utf-8') as f:
        return f.read()
