Breaking changes
----------------

*   Switch from a namespace package to a regular package. (:issue:`kurtmckee/feedparser#585`)

    The choice to use a namespace package caused development issues in feedparser,
    and affected deployments for users.

    The new package name is ``feedparser_sgmllib``.
