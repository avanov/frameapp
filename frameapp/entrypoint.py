import re
from typing import Dict, List, Optional

from .configurator import Configurator


def setup(package: str, apps: Dict[List[Dict[str, str]]], namespace='frameapp', ignore: Optional[List[str]] = None) -> Configurator:
    configurator = Configurator()

    for app_name, entry_points in apps.items():
        for entry_point in entry_points:
            configurator.include(app_name, entry_point['entry_point'], entry_point['url_prefix'], namespace)

    if ignore is None:
        ignore = [
            '.__pycache__',
            # do not scan migrations
            re.compile('^.*\.?migrations\.?.*$').match,
            # do not scan test modules included into the project tree
            re.compile('^.*\.?tests\.?.*$').match,
        ]

    configurator.scan(
        package=package,
        namespace=namespace,
        ignore=ignore
    )
    registry = configurator.freeze()
    return configurator
