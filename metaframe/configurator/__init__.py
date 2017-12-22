""" This module is initially taken from Solo

https://github.com/avanov/solo/blob/bf44c527dbe48256d2bd3da463eceeb78d05a38d/solo/configurator/__init__.py
"""
from typing import Optional
from types import ModuleType
import logging
import inspect

import venusian

from .. import registry
from ..util import maybe_dotted
from ..exceptions import ConfigurationError
from ..path import caller_package

from .routes import RoutesConfigurator
from .views import ViewsConfigurator
from .renderers import RenderersConfigurator
from .sums import SumTypesConfigurator


log = logging.getLogger(__name__)


class Configurator:
    """ Every Configurator has its own registry.
    The global app registry this particular configurator produces, is a product of all other configurators combined.
    """
    venusian = venusian
    inspect = inspect

    def __init__(self,
                 routes_configurator=RoutesConfigurator,
                 views_configurator=ViewsConfigurator,
                 renderers_configurator=RenderersConfigurator,
                 sum_types_configurator=SumTypesConfigurator
                 ) -> None:
        self._registry = registry._RegistryBuilder()
        self.registry = None
        self.routes = routes_configurator()
        self.views = views_configurator()
        self.renderers = renderers_configurator()
        self.sums = sum_types_configurator()

    def include(self,
                callable,
                entry_point: 'str' = 'includeme',
                route_prefix: Optional[str] = None,
                namespace: Optional[str] = None) -> None:
        """
        :param callable: package to be configured
        :param route_prefix:
        :return:
        """
        configuration_section: ModuleType = maybe_dotted(callable)
        if namespace is None:
            namespace = configuration_section.__package__
        old_namespace = self.routes.change_namespace(namespace)

        module = self.inspect.getmodule(configuration_section)
        if module is configuration_section:
            try:
                configuration_section = getattr(module, entry_point)
                log.debug(f'Including {callable}:{entry_point}')
            except AttributeError:
                raise ConfigurationError(
                    f"""Package "{module.__name__}" has no entry point called '{entry_point}'. """
                    "Make sure you have defined it."
                )

        sourcefile = self.inspect.getsourcefile(configuration_section)

        if sourcefile is None:
            raise ConfigurationError(
                f'No source file for module {module.__name__} (.py file must exist, '
                f'refusing to use orphan .pyc or .pyo file).'
            )

        if route_prefix is None:
            route_prefix = ''
        route_prefix = f"{self.routes.route_prefix.rstrip('/')}/{route_prefix.lstrip('/')}"
        old_route_prefix = self.routes.change_route_prefix(route_prefix)

        self._log_caption(f'Configuring {callable}:{entry_point}')
        configuration_section(self)
        self.routes.change_namespace(old_namespace)
        self.routes.change_route_prefix(old_route_prefix)

    def scan(self, package=None, categories=None, onerror=None, ignore=None, namespace=None):
        if package is None:
            package = caller_package()

        package = maybe_dotted(package)

        if namespace is None:
            namespace = package.__name__

        self._log_caption(f'Scanning {package}')
        scanner = Scanner(configurator=self)
        previous_namespace = scanner.configurator.routes.change_namespace(namespace)

        scanner.scan(package, categories=categories, onerror=onerror, ignore=ignore)

        self._log_caption('Consistency check')
        self.routes.check_routes_consistency(namespace)
        self.sums.check_sum_types_consistency(namespace)

        self.routes.change_namespace(previous_namespace)
        self._log_caption(f'End scanning {package}')

    def freeze(self) -> registry.AppRegistry:
        self.registry = registry.AppRegistry(*self._registry.as_dict())
        return self.registry

    def _log_caption(self, caption) -> None:
        caption = f' {caption} '
        cap_len = len(caption)
        total_len = 100
        sep_len = int((total_len - cap_len) / 2)
        sep = "-" * sep_len
        log.debug(f'{sep}{caption}{sep}')


class Scanner(venusian.Scanner):
    configurator: Configurator
