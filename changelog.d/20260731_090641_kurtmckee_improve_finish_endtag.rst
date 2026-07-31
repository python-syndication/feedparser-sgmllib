Changed
-------

*   Improve the closing tag search behavior of ``SGMLParser.finish_endtag()``.

    Previously, the method always searched the entire tag stack
    to close the innermost tag, which had a higher search cost.
    The tag stack is now searched in reverse order
    and breaks on the first matching tag.
