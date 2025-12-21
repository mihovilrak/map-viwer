import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

project = 'Map View API'
copyright = '2025, Mihovil Rak'
author = 'Mihovil Rak'
release = '0.1.0'

templates_path = ['_templates']
exclude_patterns = [
    '.venv',
    'venv',
    '.complexipy_cache',
    '.pytest_cache',
    '.ruff_cache',
    '.mypy_cache',
    '.pytest_cache',
]

html_theme = 'alabaster'
html_static_path = ['_static']

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'sphinx_autodoc_typehints',
    'myst_parser',
]

autosummary_generate = True
autosummary_imported_members = False

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_use_param = True
napoleon_use_ivar = False

html_theme = 'sphinx_rtd_theme'

autodoc_default_options = {
    'members': True,
    'undoc-members': False,
    'show-inheritance': True,
    'special-members': False,
}

autodoc_mock_imports = [
    'rio_tiler',
    'rio_tiler.io',
    'rasterio',
    'rasterio.crs',
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

html_theme_options = {
    'prev_next_buttons_location': 'bottom',
}

html_sidebars = {
    '**': [
        'globaltoc.html',
        'relations.html',
        'searchbox.html',
    ]
}

suppress_warnings = ['app.add_object_type']
