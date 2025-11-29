# Configuration file for the Sphinx documentation builder.

import os
import sys

from aubellhop import __version__

# Add Python package path
conf_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(conf_dir, "..", ".."))
sys.path.insert(0, project_root)

# Add custom extensions directory
sys.path.insert(0, os.path.abspath('_ext'))

# -- Project information -----------------------------------------------------
project = 'AUBELLHOP: Python wrapper and driver for Bellhop'
copyright = '2025 Will Robertson'
author = 'Will Robertson, Mandar Chitre'
release = __version__
version = __version__

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'dataclass_table',
    "sphinxcontrib.mermaid",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

autodoc_mock_imports = ["matplotlib", "gcovr", "numpy", "scipy", "pandas", "bokeh"]

# Avoid linking built-in types like typing.Any, typing.Optional, etc.
autodoc_type_aliases = {}
nitpick_ignore = [
    ("py:class", "Any"),
    ("py:class", "typing.Any"),
]

# -- Options for HTML output -------------------------------------------------
html_theme = 'alabaster'
#html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = True

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'undoc-members': True,
}
