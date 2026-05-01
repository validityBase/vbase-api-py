import os
import sys

from sphinx_markdown_builder.translator import (
    MarkdownTranslator as MarkdownTranslatorBase,
)
from sphinx_markdown_builder.translator import TitleContext, pushing_context

# Ensure the package source is discoverable for autodoc
sys.path.insert(0, os.path.abspath('../src'))

project = 'vbase-api'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]

master_doc = 'index'
source_suffix = '.rst'
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Autodoc defaults
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'exclude-members': 'add_note,with_traceback',
}

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False


class CustomMarkdownTranslator(MarkdownTranslatorBase):
    """Render class signatures as ## and method signatures as ###."""

    @pushing_context
    def visit_desc_signature(self, node):
        if self.config.markdown_anchor_signatures:
            for anchor in node.get("ids", []):
                self._add_anchor(anchor)

        h_level = 3 if node.get("class", None) else 2
        self._push_context(TitleContext(h_level))


def setup(app):
    app.set_translator("markdown", CustomMarkdownTranslator, override=True)
