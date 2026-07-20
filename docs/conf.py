import pathlib
import tomllib

# General configuration
# ---------------------

# The suffix of source filenames.
source_suffix = {".rst": "restructuredtext"}

# The main toctree document.
master_doc = "index"

# General information about the project.
project = "feedparser-sgmllib"
copyright = "Python contributors"

# Extract the project version.
pyproject_ = pathlib.Path(__file__).parent.parent / "pyproject.toml"
info_ = tomllib.loads(pyproject_.read_text())
version = release = info_["project"]["version"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"


# HTML theme configuration
# ------------------------

html_theme = "classic"

# Don't copy source .rst files into the built documentation.
html_copy_source = False
