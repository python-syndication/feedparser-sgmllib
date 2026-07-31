Fixed
-----

*   Fix quadratic search behavior in ``SGMLParser.feed()``.

    This can occur when a large document with an unfinished token
    (like ``<a href="...``) is fed into the parser in very small increments.
