""" This module is initially taken from Solo

https://github.com/avanov/solo/blob/bf44c527dbe48256d2bd3da463eceeb78d05a38d/solo/configurator/config/rendering.py
"""
from typing import Dict, Any, TypeVar, List, Generator
from enum import Enum
from decimal import Decimal
from collections import KeysView, ValuesView, ItemsView
from datetime import datetime, tzinfo

from pytz.tzinfo import BaseTzInfo
from wrapt import ObjectProxy
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest, HttpResponse
from rest_framework.utils import encoders


JsonPayload = TypeVar('JsonApiPayload', Dict[str, Any], List[Dict[str, Any]])


class JsonRendererFactory:
    def __init__(self, name: str) -> None:
        self.name = name

    def __call__(self, request: HttpRequest, view_response: JsonPayload) -> HttpResponse:
        return HttpResponse(status=200,
                            content=encode_json(view_response).encode('utf-8'),
                            content_type='application/json',
                            charset='utf-8')


class StringRendererFactory:
    def __init__(self, name: str) -> None:
        self.name = name

    def __call__(self, request: HttpRequest, view_response: Any):
        HttpResponse(status=200,
                     content=str(view_response).encode('utf-8'),
                     content_type='text/plain',
                     charset='utf-8')


BUILTIN_RENDERERS = {
    'json': JsonRendererFactory,
    'string': StringRendererFactory,
}


class RenderersConfigurator:

    def __init__(self) -> None:
        self.registry = {}
        for name, renderer in BUILTIN_RENDERERS.items():
            self.add_renderer(name, renderer)

    def add_renderer(self, name: str, factory):
        self.registry[name] = factory

    def get_renderer(self, name: str):
        try:
            template_suffix = name.rindex(".")
        except ValueError:
            # period is not found
            renderer_name = name
        else:
            renderer_name = name[template_suffix:]

        try:
            rv = self.registry[renderer_name](name)
        except KeyError:
            raise ValueError(f'No such renderer factory "{renderer_name}"')
        return rv


class ExtendedJSONEncoder(encoders.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if hasattr(obj, '__json__'):
            return obj.__json__()
        elif isinstance(obj, (BaseTzInfo, tzinfo)):
            return str(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, ObjectProxy):
            return obj.__wrapped__

        return super().default(obj)


class ExtendedDjangoJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        """
        Check that milliseconds/microseconds are ignored when encoding datetime
        objects (we don't save them in the database, but some endpoints end up
        making them - and milliseconds break Jon's iOS JSON Decoder).
        """
        if hasattr(o, '__json__'):
            return o.__json__()
        elif isinstance(o, datetime) and o.microsecond:
            return o.replace(microsecond=0)
        # http://stackoverflow.com/questions/1960516/python-json-serialize-a-decimal-object
        elif isinstance(o, Decimal):
            return float(o)
        elif o.__class__.__name__ is '__proxy__':
            return str(o)
        elif isinstance(o, (KeysView, ValuesView, ItemsView, Generator)):
            return list(o)
        elif isinstance(o, Enum):
            return o.value

        return super().default(o)


encode_json = ExtendedDjangoJSONEncoder().encode
