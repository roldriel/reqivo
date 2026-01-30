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
    "myst_parser",
    "pallets_sphinx_themes",
]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "flask"
html_static_path = ["_static"]

html_theme_options = {
    "canonical_url": "https://roldriel.github.io/reqivo/",
}

html_context = {
    "project_name": "Reqivo",
    "github_user": "roldriel",
    "github_repo": "reqivo",
}

html_sidebars = {
    "index": ["project.html", "sidebar_nav.html", "searchbox.html", "ethicalads.html"],
    "**": ["sidebar_nav.html", "relations.html", "searchbox.html", "ethicalads.html"],
}
