import logging

from django.http import HttpResponse
from django.conf import settings
from pkg_resources import parse_version


log = logging.getLogger(__name__)


class FrameappMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """ https://docs.djangoproject.com/en/1.11/topics/http/middleware/#process-view
        """
        if 'version' in view_kwargs:
            version = parse_version(view_kwargs['version'])
            if version < settings.FRAMEAPP['MIN_API_VERSION']:
                return HttpResponse(status=410)
        else:
            log.debug(f"API Version is not specified. Defaulting to {settings.FRAMEAPP['MIN_API_VERSION']}")
            version = settings.FRAMEAPP['MIN_API_VERSION']
        setattr(request, 'API_VERSION', version)
