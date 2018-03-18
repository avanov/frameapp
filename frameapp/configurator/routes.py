import os
import logging
from collections import OrderedDict
from typing import Optional, Dict, List, NamedTuple, Any, Callable, Union, Sequence, Set, Tuple

from .sums import SumType
from ..util import viewdefaults
from ..exceptions import ConfigurationError


log = logging.getLogger(__name__)


class RoutesConfigurator:
    def __init__(self, route_prefix: str = '/', namespace: str = 'frameapp_namespace') -> None:
        self.registry: Dict[str, Dict[str, Route]] = OrderedDict()
        self.route_prefix = route_prefix
        self.namespace = namespace
        self.change_namespace(namespace)

    def change_route_prefix(self, prefix: str) -> str:
        old_prefix = self.route_prefix
        self.route_prefix = prefix
        return old_prefix

    def change_namespace(self, new: str) -> str:
        old = self.namespace
        self.namespace = new
        self.registry.setdefault(new, OrderedDict())
        return old

    def add_route(self, name: str, pattern: str, rules: Optional[Dict[str, SumType]] = None, extra_kwargs=None) -> None:
        pattern = os.path.join(self.route_prefix.rstrip('/'), pattern.lstrip('/'))
        if not pattern:
            pattern = '/'

        if rules is None:
            rules = {}

        if name in self.registry[self.namespace]:
            raise ConfigurationError(f'Route named "{name}" is already registered in the namespace "{self.namespace}"')

        log.debug(f'Registering global route "{pattern}" with the local name "{name}" in the "{self.namespace}" namespace')
        self.registry[self.namespace][name] = Route(name=name,
                                                    pattern=pattern,
                                                    rules=rules,
                                                    extra_kwargs=extra_kwargs,
                                                    view_metas=[],
                                                    # This field might be updated later
                                                    schemas=OrderedDict())

    @viewdefaults
    def add_route_schema(self,
                         view,
                         route_name: str,
                         request_method: Union[None, str, Sequence] = None,
                         attr: Optional[str] = None,
                         input_serializer: Any = None,
                         output_serializer: Any = None,
                         input_schema: Any = None,
                         output_schema: Any = None,
                         api_version: Any = None,
                         **extra_kwargs) -> None:

        route = self.registry[self.namespace][route_name]

        if any((input_serializer, output_serializer, input_schema, output_schema, api_version)):
            if request_method is None:
                request_method = ('GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS')
            else:
                if isinstance(request_method, list):
                    request_method = tuple(request_method)
                else:
                    request_method = (request_method, )

            sig = SchemaIdentifier(request_method=request_method,
                                   route_name=route_name,
                                   api_version=api_version)
            if sig in route.schemas:
                raise ConfigurationError(f'Attempt to rewrite an existing schema for {sig}')

            if attr:
                doc = getattr(view, attr).__doc__
            else:
                doc = view.__doc__

            doc = doc or 'DOCSTRING NOT SPECIFIED'

            log.debug(f'Adding schema definition for {sig}')
            route.schemas[sig] = SchemaDefinition(
                input_serializer=input_serializer,
                output_serializer=output_serializer,
                input_schema=input_schema,
                output_schema=output_schema,
                doc=doc
            )

    def check_routes_consistency(self, namespace):
        log.debug(f'Checking routes consistency for namespace "{namespace}"...')
        for route_name, route in self.registry[namespace].items():
            view_metas = route.view_metas
            if not view_metas:
                raise ConfigurationError(
                    'Route name "{name}" is not associated with a view handler in the "{namespace}" namespace.'.format(
                        name=route_name,
                        namespace=namespace
                    )
                )
            for view_item in view_metas:
                if view_item.registered_view is None:
                    raise ConfigurationError(
                        'Route name "{name}" is not associated with a view handler in the "{namespace}" namespace.'.format(
                            name=route_name,
                            namespace=namespace
                        )
                    )


class ViewMeta(NamedTuple):
    route_name: str
    registered_view: Any
    """ View object that was registered by a marker
    """
    actual_view_handler: Optional[Callable]
    """ View object that is inferred to handle requests; inference is based on the kind of `registered_view`
    """
    decorator: Optional[Callable]
    attr: Optional[str]
    renderer: Any
    predicates: Any
    is_django_generic_view: bool
    is_drf_model_viewset: bool


class SchemaIdentifier(NamedTuple):
    request_method: Tuple[str]
    route_name: str
    api_version: str


class SchemaDefinition(NamedTuple):
    input_serializer: Optional[Any]
    output_serializer: Optional[Any]
    input_schema: Optional[Any]
    output_schema: Optional[Any]
    doc: Optional[str]


class Route(NamedTuple):
    name: str
    pattern: str
    rules: Any
    extra_kwargs: Optional[Any]
    view_metas: List[ViewMeta]
    schemas: Dict[SchemaIdentifier, SchemaDefinition]


class ViewVariant(NamedTuple):
    route_name: str
    registered_view: Any
    """ View object that was registered by a marker
    """
    handler: Callable
    """ View object that is inferred to handle requests; inference is based on the kind of `registered_view`
    """
    attr: Optional[str]
    renderer: Any
    predicates: Any
