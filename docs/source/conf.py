# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "PyAdomd"
copyright = "2025, Matthew Hamilton"
author = "Matthew Hamilton"
release = "1.1.2"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
]
templates_path = ["_templates"]
exclude_patterns: list[str] = []

pygments_style = "sphinx"
highlight_language = "python3"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]

html_theme_options = {
    "navbar_center": ["navbar-nav"],
    "show_toc_level": 2,
    "show_nav_level": 2,
    "navbar_end": ["theme-switcher", "version-switcher", "navbar-icon-links"],
    "navigation_with_keys": False,
    "logo": {
        "text": "PyAdomd",
    },
    "github_url": "http://gitea.matthew-hamilton.com/PowerBI/pyadomd",
    "icon_links": [
        {
            "name": "PyPI",
            "url": "http://gitea.matthew-hamilton.com/PowerBI/pyadomd",
            "icon": "fa-solid fa-box",
        },
    ],
    "secondary_sidebar_items": ["page-toc"],
}
suppress_warnings = [
    "docutils",
]
