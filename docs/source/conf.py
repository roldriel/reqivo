import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

project = "Reqivo"
copyright = "2026, Rodrigo Ezequiel Roldán"
author = "Rodrigo Ezequiel Roldán"
import reqivo

release = reqivo.__version__

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = []

# MyST-Parser configuration
myst_heading_anchors = 3
myst_all_links_external = False
myst_enable_extensions = ["colon_fence"]

# Intersphinx mapping for external references
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# Suppress warnings (cosmetic issues that don't affect documentation)
suppress_warnings = [
    "myst.xref_missing",  # External file links Sphinx can't resolve
    "ref.python",  # Duplicate cross-reference warnings from re-exports
    "ref.class",  # External class references (asyncio, socket, etc.)
    "autodoc",  # All autodoc warnings including duplicates
]

# Autodoc configuration
autodoc_default_options = {
    "imported-members": False,
    "show-inheritance": True,
}
autodoc_class_content = "init"
autodoc_member_order = "bysource"

# Furo theme configuration
html_theme = "furo"
html_static_path = ["_static"]
html_baseurl = "https://roldriel.github.io/reqivo/"

html_theme_options = {
    "source_repository": "https://github.com/roldriel/reqivo",
    "source_branch": "master",
    "source_directory": "docs/source/",
    "light_css_variables": {
        "color-brand-primary": "#2962FF",
        "color-brand-content": "#2962FF",
    },
    "dark_css_variables": {
        "color-brand-primary": "#82B1FF",
        "color-brand-content": "#82B1FF",
    },
}

html_title = "Reqivo"
