Fixed
-----

*   Close tags more correctly, even if the end tag has trailing text.

    For example, ``</tag bonus>`` now closes ``<tag>`` correctly.
    The trailing content is not available to parsers.
