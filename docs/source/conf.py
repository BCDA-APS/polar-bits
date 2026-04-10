# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import pathlib

_src_dir = pathlib.Path(__file__).parents[2] / "src"

# -- Project information -----------------------------------------------------
project = "polar-bits"
copyright = "2014-2025, APS"
author = "Eric Codrea, Pete Jemian, Rafael Vescovi"
release = "0.0.1"

# -- General configuration ---------------------------------------------------
extensions = [
    "autoapi.extension",
    "myst_parser",
    "nbsphinx",
    "sphinx_design",
    "sphinx_tabs.tabs",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "substitution",
]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Suppress noisy-but-harmless warnings from autoapi cross-module import
# resolution (imports that rely on EPICS/ophyd at runtime are unresolvable
# in a static-analysis-only build).
suppress_warnings = [
    "autoapi.python_import_resolution",
]

# -- sphinx-autoapi ----------------------------------------------------------
autoapi_dirs = [str(_src_dir)]
autoapi_root = "api"
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    # "show-module-summary" omitted: generates autosummary tables that require
    # the package to be importable — not possible in CI without EPICS/hklpy.
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
# Don't execute notebooks at build time — EPICS is not available in CI
nbsphinx_execute = "never"
