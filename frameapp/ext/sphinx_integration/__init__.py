""" http://www.sphinx-doc.org/en/stable/extdev/appapi.html

This integration allows you to construct a new sphinx directive that would output API docs for registered endpoints.

In your project, create a snippet that would look like this

.. code-block:: python

    # myapp/sphinx_integration.py
    from typing import Dict, Any
    from sphinx.application import Sphinx

    from frameapp import entrypoint
    from frameapp.ext.sphinx_integration.directives import APIDocDirective

    def setup(app: Sphinx) -> Dict[str, Any]:
        config = entrypoint.setup(
            package='myapp',
            apps=<applications>,
            namespace='myapp',
            ignore=<ignore_patterns>
        )
        app.add_directive('myapp-api-doc', APIDocDirective)
        app.add_config_value('FRAMEAPP_CONFIG', config, rebuild='html')
        return {'version': '1.0', 'parallel_read_safe': False}

Then, go to your Sphinx conf.py and find the `extensions = [ ... ]` list and add your newly created extension into it:

.. code-block:: python

    # docs/conf.py
    extensions = [
        'sphinx.ext.autodoc',
        'sphinx.ext.doctest',
        ...
        'myapp.sphinx_integration',
    ]

Now, you can use the directive in your docs

..  code-block::

    =======================
    Endpoints Documentation
    =======================

    .. myapp-api-doc::
        :prefix: /v{version:[0-9]+\.[0-9]+}


"""
