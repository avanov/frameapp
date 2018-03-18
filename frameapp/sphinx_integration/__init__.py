from typing import Dict, Any

from sphinx.application import Sphinx

from .directives import APIDocDirective

from .. import entrypoint


def setup(app: Sphinx) -> Dict[str, Any]:
    """ http://www.sphinx-doc.org/en/stable/extdev/appapi.html
    """
    app.add_directive('frameapp-api-doc', APIDocDirective)
    app.add_config_value('FRAMEAPP_CONFIG', entrypoint.setup(), rebuild='html')
    return {'version': '1.0', 'parallel_read_safe': False}
