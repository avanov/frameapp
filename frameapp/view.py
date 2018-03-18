import logging
from typing import List, Dict, Union, Optional

from django.http.request import HttpRequest as DjangoRequest
from django.http.response import HttpResponse as DjangoResponse
from django.http import Http404 as HTTPNotFound
from rest_framework.request import Request as DRFRequest
from rest_framework.response import Response as DRFResponse

from .configurator.routes import ViewVariant
from .configurator.sums import SumType


log = logging.getLogger(__name__)


HttpRequest = Union[DjangoRequest, DRFRequest]
HttpResponse = Union[DjangoResponse, DRFResponse]


class PredicatedHandler:
    """ Wrapper object around actual view handlers that checks predicates during the request
    and processes results returned from view handlers during the response.
    """
    __slots__ = ['rules', 'view_variants', 'csrf_exempt']

    def __init__(self, rules: Dict[str, SumType], view_variants: List[ViewVariant]) -> None:
        self.view_variants = view_variants
        # Note that the entire PredicatedHandler will be CSRF-exempt if at least one handler is exempt.
        # This is not the ideal solution, yet it allows us to encapsulate the logic inside this object
        # instead of implementing csrf check on individual handlers in the middleware, when predicates are matched
        # and the final handler is known.
        # Most of the time it's what we need anyway, because we don't put non-api views inside DRF APIView subclasses.
        self.csrf_exempt = any(getattr(v.handler, 'csrf_exempt', False) for v in view_variants)
        self.rules = rules

    def match_predicates(self, request: HttpRequest) -> Optional[ViewVariant]:
        for view_variant in self.view_variants:
            for predicate in view_variant.predicates:
                if not predicate(None, request):
                    log.debug(f'Predicate {predicate} failed for {request.method} {request.path}')
                    break
            else:
                return view_variant
        return None

    def __call__(self, request: HttpRequest, *route_args, **route_kwargs) -> HttpResponse:
        """ Try to resolve predicates and call a view handler on success.
        """
        # here predicate is an instance object
        matched_view_variant = self.match_predicates(request)
        if matched_view_variant:
            # All predicates match, proceed to view handler invocation
            log.debug(f'{request.method} {request.path} will be handled by {matched_view_variant.handler}')
            handler = matched_view_variant.handler
            context = {}
            rules = self.rules
            for k, v in route_kwargs.items():
                if k in rules:  # match SumType's case
                    context[k] = self.rules[k].match(v)
                else:  # regular value assignment
                    context[k] = v

            response = handler(request, *route_args, **route_kwargs)
            #     # else:
            #     #     # Handler is a Pyramid-like class view.
            #     #     handler = getattr(handler(request, context), matched_view_variant.attr)
            #     #     response = handler()
            # else:
            #     # handler is a simple callable
            #     response = handler(request, context, *route_args, **route_kwargs)

            if isinstance(response, DjangoResponse):
                # Do not process standard responses
                final_response = response
            else:
                renderer = matched_view_variant.renderer
                final_response = renderer(request, response)

            return final_response

        log.debug(f'All predicates have failed for {request.method} {request.path}')
        raise HTTPNotFound()
