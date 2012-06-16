# encoding: utf-8
import sys, os

extensions = ['sphinx.ext.autodoc']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = u'Sarge'
copyright = u'2012, Alex Morega'
version = '0.1'
release = '0.1'
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
html_static_path = ['_static']
htmlhelp_basename = 'Sargedoc'

# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'sarge', u'Sarge Documentation',
     [u'Alex Morega'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False
