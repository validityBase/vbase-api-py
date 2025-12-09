import os
import sys

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
