# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import pathlib
import sys

# Make the source packages importable for type stubs (autoapi does not require
# this, but intersphinx benefits from it).
sys.path.insert(0, str(pathlib.Path(__file__).parents[2] / "src"))

# -- Project information -----------------------------------------------------
project = "polar-bits"
copyright = "2014-2025, APS"
author = "Eric Codrea, Pete Jemian, Rafael Vescovi"
release = "0.0.1"

# -- General configuration ---------------------------------------------------
extensions = [
    "autoapi.extension",  # sphinx-autoapi: no package import required
    "myst_parser",  # Markdown source files
    "nbsphinx",  # Jupyter notebook integration
    "sphinx_design",  # cards, grids, badges
    "sphinx_tabs.tabs",  # tabbed content blocks
    "sphinx.ext.intersphinx",  # cross-links to external projects
    "sphinx.ext.napoleon",  # NumPy / Google docstring styles
    "sphinx.ext.viewcode",  # [source] links in API reference
]

# MyST extensions for richer Markdown
myst_enable_extensions = [
    "colon_fence",  # ::: directive syntax
    "deflist",
    "substitution",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- sphinx-autoapi ----------------------------------------------------------
autoapi_dirs = [str(pathlib.Path(__file__).parents[2] / "src")]
autoapi_root = "api"
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]
# Skip test files, conftest, and version files
autoapi_ignore = [
    "*/test_*",
    "*/tests/*",
    "*/conftest*",
    "*/_version*",
]
# Keep autoapi output in the build (don't delete after build)
autoapi_keep_files = True
# Don't add autoapi toctree automatically; we include it manually in index.md
autoapi_add_toctree_entry = False

# -- Intersphinx -------------------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "ophyd": ("https://blueskyproject.io/ophyd/", None),
    "bluesky": ("https://blueskyproject.io/bluesky/", None),
    "apstools": ("https://bcda-aps.github.io/apstools/latest/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

# -- HTML output -------------------------------------------------------------
html_theme = "pydata_sphinx_theme"
html_title = "polar-bits"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

html_theme_options = {
    "github_url": "https://github.com/BCDA-APS/polar-bits",
    "use_edit_page_button": True,
    "show_toc_level": 2,
    "navbar_align": "left",
    "footer_start": ["copyright"],
    "footer_end": ["sphinx-version"],
    "navigation_with_keys": True,
    "logo": {
        "text": "polar-bits",
    },
}

html_context = {
    "github_user": "BCDA-APS",
    "github_repo": "polar-bits",
    "github_version": "main",
    "doc_path": "docs/source",
}

# -- nbsphinx ----------------------------------------------------------------
nbsphinx_execute = "never"  # don't execute notebooks at build time (no EPICS)
nbsphinx_allow_errors = False
