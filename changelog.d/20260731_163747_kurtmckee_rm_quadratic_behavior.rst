Fixed
-----

*   Fix quadratic CPU usage in ``SGMLParser.feed()``.

    This can occur when a large document with an unfinished token
    (like ``<a href="...``) is fed into the parser in very small increments.

    The new implementation doesn't significantly change peak memory usage.
