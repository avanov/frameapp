""" This module is initially taken from Solo

https://github.com/avanov/solo/blob/bf44c527dbe48256d2bd3da463eceeb78d05a38d/solo/configurator/config/views.py
"""
import inspect
import logging
from collections import OrderedDict
from typing import Optional

from django.views.generic.base import View as DjangoGenericView

from . import predicates as default_predicates
from ..util import viewdefaults
from .routes import ViewMeta
from .util import PredicateList
from ..exceptions import ConfigurationError


log = logging.getLogger(__name__)


class ViewsConfigurator:

    def __init__(self) -> None:
        self.registry = OrderedDict()
        self.predicates = PredicateList()
        self.add_default_view_predicates()

    @viewdefaults
    def add_view(self,
                 view=None,
                 route_name: Optional[str] = None,
                 request_method=None,
                 attr=None,
                 decorator=None,
                 renderer=None,
                 **predicates) -> ViewMeta:
        """

        :param view: callable
        :param route_name:
        :param request_method:
        :type request_method: str or tuple
        :param attr:
          This knob is most useful when the view definition is a class.

          The view machinery defaults to using the ``__call__`` method
          of the :term:`view callable` (or the function itself, if the
          view callable is a function) to obtain a response.  The
          ``attr`` value allows you to vary the method attribute used
          to obtain the response.  For example, if your view was a
          class, and the class has a method named ``index`` and you
          wanted to use this method instead of the class' ``__call__``
          method to return the response, you'd say ``attr="index"`` in the
          view configuration for the view.
        :type attr: str
        :param decorator:
        :param renderer:
        :param predicates: Pass a key/value pair here to use a third-party predicate
                           registered via
                           :meth:`solo.configurator.config.Configurator.views.add_view_predicate`.
                           More than one key/value pair can be used at the same time. See
                           :ref:`view_and_route_predicates` for more information about
                           third-party predicates.
        :return: :raise ConfigurationError:
        """
        from rest_framework.viewsets import ViewSetMixin

        # Prepare view object
        # -------------------------------------
        is_django_generic_view = issubclass(view, DjangoGenericView)
        is_drf_model_viewset = issubclass(view, ViewSetMixin)

        if inspect.isclass(view):
            if attr is None:
                attr = '__call__'
            if not issubclass(view, DjangoGenericView) and not hasattr(view, attr):
                raise ConfigurationError(f"View {view} is registered as a callable, but didn't define its __call__ method.")

        # Add decorators
        # -----------------------------------------------
        def combine(*decorators):
            def decorated(view_callable):
                # reversed() is allows a more natural ordering in the api
                for decorator in reversed(decorators):
                    view_callable = decorator(view_callable)
                return view_callable
            return decorated

        if isinstance(decorator, (tuple, list)):
            decorator = combine(*decorator)

        # Register predicates
        # -------------------------------------
        if request_method is None:
            request_method = ('GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS')
        pvals = predicates.copy()
        pvals.update(dict(request_method=request_method,))
        predlist = self.get_predlist('view')
        _weight_, preds, _phash_ = predlist.make(self, **pvals)

        # Renderers
        # -------------------------------------
        if renderer is None:
            renderer = 'string'

        # Done
        # -------------------------------------
        view_item = ViewMeta(route_name=route_name,
                             registered_view=view,
                             actual_view_handler=None,
                             decorator=decorator,
                             attr=attr,
                             renderer=renderer,
                             predicates=preds,
                             is_django_generic_view=is_django_generic_view,
                             is_drf_model_viewset=is_drf_model_viewset)

        log.debug(f'View added: {view_item}')
        return view_item

    def get_predlist(self, name: str):
        """ This is a stub method that simply has the same signature as pyramid's version,
        but does nothing but returning ``self.predicates``
        """
        return self.predicates

    def add_view_predicate(self, name, factory, weighs_more_than=None,
                           weighs_less_than=None):
        """
        Adds a view predicate factory.  The associated view predicate can
        later be named as a keyword argument to
        :meth:`solo.configurator.config.Configurator.views.add_view` in the
        ``predicates`` anonymous keyword argument dictionary.

        ``name`` should be the name of the predicate.  It must be a valid
        Python identifier (it will be used as a keyword argument to
        ``add_view`` by others).

        ``factory`` should be a :term:`predicate factory` or :term:`dotted
        Python name` which refers to a predicate factory.

        See :ref:`view_and_route_predicates` for more information.
        """
        self._add_predicate(
            'view',
            name,
            factory,
            weighs_more_than=weighs_more_than,
            weighs_less_than=weighs_less_than
        )

    def add_default_view_predicates(self):
        p = default_predicates
        for name, factory in (('request_method', p.RequestMethodPredicate),
                              ('api_version', p.ApiVersionPredicate),
                              ('output_serializer', p.OutputSerializerPredicate),
                              ('input_schema', p.InputSchemaPredicate),
                              ('output_schema', p.OutputSchemaPredicate),):
            self.add_view_predicate(name, factory)

    def _add_predicate(self, type: str, name: str, factory, weighs_more_than=None, weighs_less_than=None):
        """ This method is a highly simplified equivalent to what you can find in Pyramid.

        :param type: may be only 'view' at the moment
        :param name: valid python identifier string.
        :param weighs_more_than: not used at the moment
        :param weighs_less_than: not used at the moment
        """
        predlist = self.get_predlist(type)
        predlist.add(name, factory, weighs_more_than=weighs_more_than,
                     weighs_less_than=weighs_less_than)
