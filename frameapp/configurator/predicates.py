""" This module is initially taken from Solo

https://github.com/avanov/solo/blob/bf44c527dbe48256d2bd3da463eceeb78d05a38d/solo/configurator/config/predicates.py
"""
import operator
from typing import Optional

import jsonschema
from django.http import HttpRequest
from pkg_resources import SetuptoolsVersion
from pkg_resources import parse_version
from rest_framework.request import Request

from ..schemas import json_schema
from .util import as_sorted_tuple


class RequestMethodPredicate:
    def __init__(self, val, config, raises: Optional[Exception] = None) -> None:
        """ Predicates are constructed at ``solo.configurator.config.util.PredicateList.make()``

        :param val: value passed to http_endpoint/http_defaults
        :param config:
        """
        request_method = as_sorted_tuple(val)
        if 'GET' in request_method and 'HEAD' not in request_method:
            # GET implies HEAD too
            request_method = as_sorted_tuple(request_method + ('HEAD',))
        self.val = request_method
        self.raises = raises

    def text(self) -> str:
        return 'request_method<%s>' % (','.join(self.val))

    phash = text
    __repr__ = text

    def __call__(self, context: Optional, request: HttpRequest) -> bool:
        """
        :param context: at the moment context may be only None
        :type context: None
        :param: request: Django request object
        :type request: :class:`django.http.HttpRequest`
        """
        return request.method in self.val


class ApiVersionPredicate:
    OPERATORS = {
        '>': operator.gt,
        '<': operator.lt,
        '==': operator.eq,
        '>=': operator.ge,
        '<=': operator.le
    }

    def __init__(self, val, config, raises: Optional[Exception] = None) -> None:
        """
        :param val: value passed to view_config/view_defaults
        :param config:
        """
        api_version = as_sorted_tuple(val)
        self.val = api_version
        self.raises = None

    def text(self) -> str:
        return f'api_version<{self.val}>'

    phash = text
    __repr__ = text

    def __call__(self, context: Optional, request: HttpRequest) -> bool:
        """
        :param context: at the moment context may be only None
        :type context: None
        :param: request: Django request object
        :type request: :class:`django.http.HttpRequest`
        """
        for allowed_api_pattern in self.val:
            if self.match_api_version(request.API_VERSION, allowed_api_pattern):
                return True
        return False

    def match_api_version(self, request_version: SetuptoolsVersion, allowed_version) -> bool:
        """

        :param request_version:
        :param allowed_version: may be represented in following forms:
            1. ``VERSION``
            2. ``==VERSION`` (the same as above)
            3. ``>VERSION``
            4. ``<VERSION``
            5. ``>=VERSION``
            6. ``<=Version``
            7. Comma-separated list of 1-7 evaluated as AND
        :return: :raise ValueError:
        """
        distinct_versions = {version.strip() for version in allowed_version.split(',')}
        for distinct_version in distinct_versions:
            operation = self.OPERATORS.get(distinct_version[:2])
            if operation:
                # prepare cases #2, #5, #6
                compare_with = distinct_version[2:]
            else:
                operation = self.OPERATORS.get(distinct_version[0])
                if operation:
                    # prepare cases #3, #4
                    compare_with = distinct_version[1:]
                else:
                    # prepare case #1
                    compare_with = distinct_version
                    operation = self.OPERATORS['==']

            # evaluate the case
            matched = operation(request_version, parse_version(compare_with))
            return matched
        return True


class OutputSerializerPredicate:
    def __init__(self, val, config, raises: Optional[Exception] = None) -> None:
        """ Predicates are constructed at ``solo.configurator.config.util.PredicateList.make()``

        :param val: value passed to http_endpoint/http_defaults
        :param config:
        """

        self.val = val
        self.raises = raises

    def text(self) -> str:
        return f'output_serializer<{self.val.__name__}>'

    phash = text
    __repr__ = text

    def __call__(self, context: Optional, request: HttpRequest) -> bool:
        """
        :param context: at the moment context may be only None
        :type context: None
        :param: request: Django request object
        :type request: :class:`django.http.HttpRequest`
        """
        return True


class InputSchemaPredicate:
    def __init__(self, val, config, raises: Optional[Exception] = None) -> None:
        """ Predicates are constructed at ``solo.configurator.config.util.PredicateList.make()``

        :param val: value passed to http_endpoint/http_defaults
        :param config:
        """
        if val.endswith('.json'):
            self.val_file = val
            self.val = json_schema(val)
        else:
            self.val_file = None
            self.val = val

        self.raises = raises

    def text(self) -> str:
        if self.val_file:
            rv = f'input_schema<{self.val}>'
        else:
            rv = f'input_schema<...>'
        return rv

    phash = text
    __repr__ = text

    def __call__(self, context: Optional, request: Request) -> bool:
        jsonschema.validate(request.data, self.val)
        return True


class OutputSchemaPredicate:
    def __init__(self, val, config, raises: Optional[Exception] = None) -> None:
        """ Predicates are constructed at ``solo.configurator.config.util.PredicateList.make()``

        :param val: value passed to http_endpoint/http_defaults
        :param config:
        """

        self.val = val
        self.raises = raises

    def text(self) -> str:
        if self.val.endswith('.json'):
            rv = f'output_schema<{self.val}>'
        else:
            rv = f'output_schema<...>'
        return rv

    phash = text
    __repr__ = text

    def __call__(self, context: Optional, request: HttpRequest) -> bool:
        """
        :param context: at the moment context may be only None
        :type context: None
        :param: request: Django request object
        :type request: :class:`django.http.HttpRequest`
        """
        return True
