# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "dronewq"
copyright = "2025, Anna Windle, Patrick Gray"
author = "Anna Windle, Patrick Gray"
release = "1.0.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

import sys
from pathlib import Path

# sys.path.insert(0, os.path.abspath('../../')) # Source code dir relative to this file
sys.path.insert(0, str(Path("..", "..").resolve()))

extensions = [
    "sphinx.ext.autodoc",  # To generate autodocs
    "sphinx.ext.mathjax",  # autodoc with maths
    "sphinx.ext.napoleon",  # For auto-doc configuration
    "sphinx.ext.autosummary",  # Create neat summary tables
    "myst_parser",  # to read markdown
    "nbsphinx",  # to read jupyter notebooks
]

napoleon_google_docstring = False  # Turn off googledoc strings
napoleon_numpy_docstring = True  # Turn on numpydoc strings
napoleon_use_ivar = True  # For maths symbology

autosummary_generate = True  # Turn on sphinx.ext.autosummary

templates_path = ["_templates"]
exclude_patterns = []

# extensions = []

source_suffix = [".rst", ".md"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
