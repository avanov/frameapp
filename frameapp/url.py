""" Initially taken from Solo

https://github.com/avanov/solo/blob/86695ede6f69a9a162943a4db03dd412ee3419c6/solo/configurator/url.py
"""
import re
import logging
from typing import Dict, List, Tuple, NamedTuple, Any, Optional, Type

from django.http import HttpRequest
from django.urls import URLPattern
from django.urls.resolvers import RegexPattern
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework import routers

from .exceptions import ConfigurationError
from .configurator import Configurator
from .configurator.sums import SumType
from .configurator.routes import ViewVariant
from .util import maybe_dotted
from .view import PredicatedHandler

log = logging.getLogger(__name__)


# A replacement marker in a pattern must begin with an uppercase or
# lowercase ASCII letter or an underscore, and can be composed only
# of uppercase or lowercase ASCII letters, underscores, and numbers.
# For example: a, a_b, and b9 are all valid replacement marker names, but 0a is not.
ROUTE_PATTERN_OPEN_BRACES_RE = re.compile('(?P<start_brace>\{).*')
ROUTE_PATTERN_CLOSING_BRACES_RE = re.compile('\}.*')
EMBEDDED_SUM_TYPE_RE = re.compile('\<(?P<sum_type>[a-zA-Z0-9_.:]+)\>')


class Dispatcher(NamedTuple):
    route_namespace: str
    route_name: str
    route_pattern: str
    route_rules: Any
    route_schemas: Any
    route_extra_kwargs: Optional[Any]
    view_variants: List[ViewVariant]


def _extract_braces_expression(line: str, starting_braces_re, open_braces_re, closing_braces_re):
    """ This function is taken from Plim package: https://pypi.python.org/pypi/Plim/

    :param line: may be empty
    :param starting_braces_re:
    :param open_braces_re:
    :param closing_braces_re:
    """
    match = starting_braces_re.match(line)
    if not match:
        return None

    open_brace = match.group('start_brace')
    buf = [open_brace]
    tail = line[len(open_brace):]
    braces_counter = 1

    while tail:
        current_char = tail[0]
        if closing_braces_re.match(current_char):
            braces_counter -= 1
            buf.append(current_char)
            if braces_counter:
                tail = tail[1:]
                continue
            return ''.join(buf), tail[1:]

        if open_braces_re.match(current_char):
            braces_counter += 1
            buf.append(current_char)
            tail = tail[1:]
            continue

        buf.append(current_char)
        tail = tail[1:]
    raise Exception(f"Unexpected end of a route pattern: {line}")


extract_pattern = (lambda line: _extract_braces_expression(
    line,
    ROUTE_PATTERN_OPEN_BRACES_RE,
    ROUTE_PATTERN_OPEN_BRACES_RE,
    ROUTE_PATTERN_CLOSING_BRACES_RE
))


def normalize_route_pattern(pattern: str) -> Tuple[str, Dict[str, SumType]]:
    buf = []
    rules = {}
    while pattern:
        result = extract_pattern(pattern)
        if result:
            extracted, pattern = result
            if ':' in extracted:
                # Remove braces from the extracted result "{pattern[:rule]}"
                pattern_name, rule = extracted[1:-1].split(':', 1)
                embedded_sum_type = EMBEDDED_SUM_TYPE_RE.match(rule)
                if embedded_sum_type:
                    sum_type = maybe_dotted(embedded_sum_type.group('sum_type'))
                    rules[pattern_name] = sum_type
                    url_part = '{{{}}}'.format(pattern_name)
                else:
                    url_part = extracted
            else:
                url_part = extracted

            buf.append(url_part)
            continue

        buf.append(pattern[0])
        pattern = pattern[1:]

    # Parsing is done. Now join everything together
    buf = ''.join(buf)
    return buf, rules


_django_rule_format = (lambda match_group_name, rule: f"(?P<{match_group_name}>{rule})")
_solo_rule_format = (lambda match_group_name, rule: f"{{{match_group_name}:{rule}}}")


def complete_route_pattern(pattern: str, rules: Dict[str, Type[SumType]], rule_format=_solo_rule_format) -> str:
    """
    :param pattern: URL pattern
    """
    buf = []
    while pattern:
        result = extract_pattern(pattern)
        if result:
            result, pattern = result
            # Remove braces from the result "{pattern[:rule]}"
            result = result[1:-1]
            if ':' in result:
                # pattern in a "pattern_name:rule" form
                match_group_name, rule = result.split(':', 1)
            else:
                # pattern in a "pattern_name" form
                match_group_name = result
                rule = rules.get(match_group_name)
                if not rule:
                    # Use default pattern
                    rule = '[^/]+'
                elif issubclass(rule, SumType):
                    # Compose SumType's regex
                    rule = '(?:{})'.format('|'.join([str(v) for v in rule.values()]))

            result = rule_format(match_group_name, rule)
            buf.append(result)
            continue

        buf.append(pattern[0])
        pattern = pattern[1:]

    # Parsing is done. Now join everything together
    buf = ''.join(buf)
    return buf


def create_django_route(dispatcher: Dispatcher) -> List[URLPattern]:
    view_variants = []
    viewset_variants = []
    for view_variant in dispatcher.view_variants:
        if isinstance(view_variant.handler, DRFViewMixinWrapper):
            vv = viewset_variants
        else:
            vv = view_variants
        vv.append(view_variant)

    rv = []
    # Prepare URLPatterns similar to http://www.django-rest-framework.org/api-guide/routers/#usage
    if view_variants:
        django_route_name = f'{dispatcher.route_namespace}.{dispatcher.route_name}'
        pattern = dispatcher.route_pattern.lstrip('/')  # removes django warnings
        pattern = complete_route_pattern(pattern, dispatcher.route_rules, _django_rule_format)
        regex_pattern = f'^{pattern}$'
        callback = PredicatedHandler(dispatcher.route_rules, view_variants)
        log.debug(f'Creating Django URL "{regex_pattern}" as the handler named "{dispatcher.route_name}" in the namespace "{dispatcher.route_namespace}".')
        rv.append(URLPattern(RegexPattern(regex_pattern, is_endpoint=True), callback, dispatcher.route_extra_kwargs, django_route_name))

    if viewset_variants:
        django_route_name = f'{dispatcher.route_namespace}.{dispatcher.route_name}-drf_viewset'
        pattern = dispatcher.route_pattern.lstrip('/')  # removes django warnings
        pattern = complete_route_pattern(pattern, dispatcher.route_rules, _django_rule_format)
        drf_pattern = '(?P<__frameapp_dynamic_viewset__>/(?P<pk>[^/.]+))?'
        regex_pattern = f'^{pattern}{drf_pattern}$'
        callback = PredicatedHandler(dispatcher.route_rules, viewset_variants)
        log.debug(f'Creating DRF URL "{regex_pattern}" as the handler named "{dispatcher.route_name}" in the namespace "{dispatcher.route_namespace}".')
        rv.append(URLPattern(RegexPattern(regex_pattern, is_endpoint=True), callback, dispatcher.route_extra_kwargs, django_route_name))
    return rv


def generate_api_docs(configurator: Configurator):
    return ''


def django_url_patterns(namespace: str, configurator: Configurator) -> List[URLPattern]:
    """ Generates Django URLs from registered routes
    """
    application_routes = configurator.routes.registry[namespace]
    rv = []
    dispatchers = []
    for route in application_routes.values():
        dispatcher = Dispatcher(
            route_namespace=namespace,
            route_name=route.name,
            route_pattern=route.pattern,
            route_rules=route.rules,
            route_schemas=route.schemas,
            route_extra_kwargs=route.extra_kwargs,
            view_variants=[]
        )
        for view_meta in route.view_metas:
            if issubclass(view_meta.registered_view, GenericViewSet):
                handler = DRFViewMixinWrapper(view_meta.registered_view)
            elif issubclass(view_meta.registered_view, APIView):
                handler = DRFAPIViewWrapper(view_meta.registered_view, view_meta.attr)
            else:
                raise ConfigurationError(f'Unknown type of view: {view_meta.registered_view}')

            if view_meta.decorator:
                # apply decorators
                handler = view_meta.decorator(handler)

            view_variant = ViewVariant(
                route_name=view_meta.route_name,
                registered_view=view_meta.registered_view,
                handler=handler,
                attr=view_meta.attr,
                renderer=view_meta.renderer,
                predicates=view_meta.predicates
            )
            dispatcher.view_variants.append(view_variant)

        dispatchers.append(dispatcher)

    for dispatcher in dispatchers:
        rv += create_django_route(dispatcher=dispatcher)

    return rv


class DRFViewMixinWrapper:
    """ Wrap DRF ViewMixin into a callable object that dispatches requests either to a collection or a item view.
    """
    def __init__(self, view_cls: Type[GenericViewSet]) -> None:
        router = routers.SimpleRouter(trailing_slash=False)
        router.register('', view_cls)
        urls: Tuple[URLPattern, URLPattern] = router.urls
        collection, item = urls
        self.collection_handler = collection.callback
        self.item_handler = item.callback
        self.csrf_exempt = any([
            getattr(self.collection_handler, 'csrf_exempt', False),
            getattr(self.item_handler, 'csrf_exempt', False),
        ])

    def __call__(self, request: HttpRequest, *args, **kwargs):
        item_suffix = kwargs.pop('__frameapp_dynamic_viewset__', '')
        if item_suffix:
            handler = self.item_handler
        else:
            handler = self.collection_handler
        return handler(request, *args, **kwargs)

    def __repr__(self) -> str:
        return f'DRFViewMixinWrapper(handler=[{self.collection_handler}, {self.item_handler}])'

    @staticmethod
    def drf_frameapp_dispatch_patched_version(self: APIView, __frameapp_view_attr__: str, request, *args, **kwargs):
        """ This portion of code is taken from DRF
        https://github.com/encode/django-rest-framework/blob/79be20a7c68e7c90dd4d5d23a9e6ee08b5f586ae/rest_framework/views.py#L465

        and then modified in order to support multiple handlers for the same request.
        __frameapp_view_attr__ will always contain a name to a method whose predicates matched the request.

        Original docstring:

        `.dispatch()` is pretty much the same as Django's regular dispatch,
        but with extra hooks for startup, finalize, and exception handling.
        """
        handler = getattr(self, __frameapp_view_attr__)
        log.debug(f'Entering patched DRF resolver with target method "{handler}"')

        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers  # deprecate?

        try:
            self.initial(request, *args, **kwargs)
            response = handler(request, *args, **kwargs)
        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response


class DRFAPIViewWrapper:
    """ Wrap DRF APIView into a callable object that dispatches requests based on view attribute name.
    """
    def __init__(self, view_cls: Type[APIView], view_attr: str) -> None:
        self.attr = view_attr
        view_cls.dispatch = _drf_frameapp_dispatch_patched_version  # this has a global side-effect, not good enough

        self.handler = view_cls.as_view()
        self.csrf_exempt = getattr(self.handler, 'csrf_exempt', False)
        # Let's monkey-patch this view class with a b/w compatible .dispatch() method that understands
        # how to dispatch to predicated methods, and then let's generate an actual view handler.
        self.handler.dispatch = _drf_frameapp_dispatch_patched_version

    def __call__(self, request, *args, **kwargs):
        # DRF GenericViewSet is similar to DRF ModelViewSet, yet we have an extra step here.
        # The handler will call a patched version of DRFs .dispatch() method that will pass data to the correct method.

        # Note however, that by the time DRF is in action, we have matched all the required predicates.
        # Best of the two worlds!
        return self.handler(self.attr, request, *args, **kwargs)


# Note: DRF API Views are made CSRF exempt from within `as_view` as to prevent
# accidental removal of this exemption in cases where `dispatch` needs to
# be overridden.
def _drf_frameapp_dispatch_patched_version(self: APIView, __frameapp_view_attr__: str, request, *args, **kwargs):
    """ This portion of code is taken from DRF
    https://github.com/encode/django-rest-framework/blob/79be20a7c68e7c90dd4d5d23a9e6ee08b5f586ae/rest_framework/views.py#L465

    and then modified in order to support multiple handlers for the same request.
    __frameapp_view_attr__ will always contain a name to a method whose predicates matched the request.

    Original docstring:

    `.dispatch()` is pretty much the same as Django's regular dispatch,
    but with extra hooks for startup, finalize, and exception handling.
    """
    handler = getattr(self, __frameapp_view_attr__)
    log.debug(f'Entering patched DRF resolver with target method "{handler}"')

    self.args = args
    self.kwargs = kwargs
    request = self.initialize_request(request, *args, **kwargs)
    self.request = request
    self.headers = self.default_response_headers  # deprecate?

    try:
        self.initial(request, *args, **kwargs)
        response = handler(request, *args, **kwargs)
    except Exception as exc:
        response = self.handle_exception(exc)

    self.response = self.finalize_response(request, response, *args, **kwargs)
    return self.response
