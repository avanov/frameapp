""" http://www.sphinx-doc.org/en/stable/extdev/markupapi.html
"""
import json
from functools import partial
from io import StringIO
from typing import List, Union, Dict, Sequence

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives import unchanged
from docutils.statemachine import ViewList
from drf_openapi.entities import OpenApiSchemaGenerator
from sphinx.util.docstrings import prepare_docstring
from sphinx.util.nodes import nested_parse_with_titles

from ..schemas import json_schema_str

from ..configurator import Configurator


class APIDocDirective(Directive):
    required_arguments = 0
    optional_arguments = 0
    has_content = False  # Whether a directive source markup has a body with some content

    option_spec = {
        'prefix': unchanged
    }

    def run(self) -> List:
        """ http://www.sphinx-doc.org/en/stable/extdev/markupapi.html#docutils.parsers.rst.Directive.run
        """
        env = self.state.document.settings.env
        app = env.app
        config: Configurator = app.config.FRAMEAPP_CONFIG
        prefix = self.options.get('prefix', '/')

        app.info('Generating API documentation from gathered project metadata')

        doc_text = StringIO()
        api_doc = []
        doc_append = api_doc.append

        for namespace, route in config.routes.registry.items():
            # doc_text.write(namespace_caption(f'Namespace: {namespace}'))
            # doc_text.write(line_separator())

            for route_name, route_struct in route.items():
                if not route_struct.pattern.startswith(prefix):
                    continue

                pattern = route_struct.pattern[len(prefix):]

                doc_text.write(url_pattern_caption(pattern))
                doc_text.write(line_separator())

                for schema_sig, schema_data in route_struct.schemas.items():
                    doc_text.write(api_version(schema_sig.api_version))
                    doc_text.write(line_separator())

                    doc_text.write(request_method(schema_sig.request_method))
                    doc_text.write(line_separator())

                    docstring = '\n'.join(prepare_docstring(schema_data.doc))
                    doc_text.write(docstring)
                    doc_text.write(line_separator())

                    if schema_data.input_schema:
                        doc_text.write(output_schema(schema_data.output_schema))
                        doc_text.write(line_separator())

                    if schema_data.input_serializer:
                        # Let's create a temp schema generator. We don't have to care about initial arguments too much
                        version = '1.10'
                        temp = OpenApiSchemaGenerator(version, '<Title>', '/url')
                        response_schema, error_status_codes = temp.get_response_object(schema_data.input_serializer.get(version), '<empty doc>')
                        doc_text.write(input_serializer(response_schema))
                        doc_text.write(line_separator())

                    if schema_data.output_serializer:
                        # Let's create a temp schema generator. We don't have to care about initial arguments too much
                        version = '1.10'
                        temp = OpenApiSchemaGenerator(version, '<Title>', '/url')
                        response_schema, error_status_codes = temp.get_response_object(schema_data.output_serializer.get(version), '<empty doc>')
                        doc_text.write(output_serializer(response_schema))
                        doc_text.write(line_separator())

                    if schema_data.output_schema:
                        doc_text.write(output_schema(schema_data.output_schema))
                        doc_text.write(line_separator())

                    doc_text.write(horizontal_separator())
                    doc_text.write(line_separator())

        # Since there's no extensive guides on how to use nested_parse(),
        # the current implementation just repeats the steps from standard extensions, such as
        # https://github.com/sphinx-doc/sphinx/blob/228fdb892af25f4b93f2760f2cd6497f2aabc0be/sphinx/ext/autosummary/__init__.py#L377-L384
        # See also http://www.sphinx-doc.org/en/stable/extdev/markupapi.html#viewlists
        doc_text.seek(0)
        vl = ViewList(doc_text.readlines())
        output = nodes.paragraph()
        nested_parse_with_titles(self.state, vl, output)
        doc_append(output)

        return api_doc


def line_separator() -> str:
    return '\n\n\n'


def namespace_caption(name: str) -> str:
    hdr = '=' * len(name)
    return f'{hdr}\n{name}\n{hdr}'


def url_pattern_caption(pattern: str) -> str:
    hdr = '-' * len(pattern)
    return f'{pattern}\n{hdr}'


def schema_block(caption: str, schema: Union[str, Dict]) -> str:
    if isinstance(schema, dict):
        schema = json.dumps(schema, indent=2)
    else:
        if schema.endswith('.json'):  # schema is a file path
            schema = json_schema_str(schema)

    buf = StringIO(schema)
    offset_aligned_schema = [f'    {line}' for line in buf.readlines()]
    schema = ''.join(offset_aligned_schema)

    return f'**{caption}:**\n\n.. code-block:: json\n    \n{schema}'


input_schema = partial(schema_block, 'Input JSON Schema')
output_schema = partial(schema_block, 'Output JSON Schema')

input_serializer = partial(schema_block, 'Input Serializer')
output_serializer = partial(schema_block, 'Output Serializer')


def api_version(value: str) -> str:
    return f'**API Version:** {value}'


def request_method(value: Sequence[str]) -> str:
    val = ', '.join(value)
    return f'**Allowed Request Methods:** {val}'


def horizontal_separator():
    return '.. raw:: html\n   \n   <hr>'
