import io
import pathlib
import time
import tracemalloc

import pytest

import feedparser_sgmllib as sgmllib


def test_doctype_decl_internal(event_collector):
    inside = """\
DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.01//EN'
         SYSTEM 'http://www.w3.org/TR/html401/strict.dtd' [
<!ELEMENT html - O EMPTY>
<!ATTLIST html
  version CDATA #IMPLIED
  profile CDATA 'DublinCore'>
<!NOTATION datatype SYSTEM 'http://xml.python.org/notations/python-module'>
<!ENTITY myEntity 'internal parsed entity'>
<!ENTITY anEntity SYSTEM 'http://xml.python.org/entities/something.xml'>
<!ENTITY % paramEntity 'name|name|name'>
%paramEntity;
<!-- comment -->
]"""
    event_collector.check_events(
        [f"<!{inside}>"],
        [
            ("decl", inside),
        ],
    )


def test_doctype_decl_external(event_collector):
    inside = "DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.01//EN'"
    event_collector.check_events(
        "<!%s>" % inside,
        [
            ("decl", inside),
        ],
    )


def test_underscore_in_attrname(event_collector):
    # SF bug #436621
    """Make sure attribute names with underscores are accepted"""
    event_collector.check_events(
        "<a has_under _under>",
        [
            ("starttag", "a", [("has_under", "has_under"), ("_under", "_under")]),
        ],
    )


def test_underscore_in_tagname(event_collector):
    # SF bug #436621
    """Make sure tag names with underscores are accepted"""
    event_collector.check_events(
        "<has_under></has_under>",
        [
            ("starttag", "has_under", []),
            ("endtag", "has_under"),
        ],
    )


def test_quotes_in_unquoted_attrs(event_collector):
    # SF bug #436621
    """Be sure quotes in unquoted attributes are made part of the value"""
    event_collector.check_events(
        "<a href=foo'bar\"baz>",
        [
            ("starttag", "a", [("href", "foo'bar\"baz")]),
        ],
    )


def test_xhtml_empty_tag(event_collector):
    """Handling of XHTML-style empty start tags"""
    event_collector.check_events(
        "<br />text<i></i>",
        [
            ("starttag", "br", []),
            ("data", "text"),
            ("starttag", "i", []),
            ("endtag", "i"),
        ],
    )


def test_processing_instruction_only(event_collector):
    event_collector.check_events(
        "<?processing instruction>",
        [
            ("pi", "processing instruction"),
        ],
    )


def test_bad_nesting(event_collector):
    event_collector.check_events(
        "<a><b></a></b>",
        [
            ("starttag", "a", []),
            ("starttag", "b", []),
            ("endtag", "a"),
            ("endtag", "b"),
        ],
    )


def test_bare_ampersands(event_collector):
    event_collector.check_events(
        "this text & contains & ampersands &",
        [
            ("data", "this text & contains & ampersands &"),
        ],
    )


def test_bare_pointy_brackets(event_collector):
    event_collector.check_events(
        "this < text > contains < bare>pointy< brackets",
        [
            ("data", "this < text > contains < bare>pointy< brackets"),
        ],
    )


@pytest.mark.parametrize(
    "source",
    (
        """<a b='v' c="v" d=v e>""",
        """<a  b = 'v' c = "v" d = v e>""",
        """<a\nb\n=\n'v'\nc\n=\n"v"\nd\n=\nv\ne>""",
        """<a\tb\t=\t'v'\tc\t=\t"v"\td\t=\tv\te>""",
    ),
)
def test_attr_syntax(event_collector, source):
    output = [("starttag", "a", [("b", "v"), ("c", "v"), ("d", "v"), ("e", "e")])]
    event_collector.check_events(source, output)


@pytest.mark.parametrize(
    "attribute",
    (
        "xxx\n\txxx",
        "yyy\t\nyyy",
        "\txyz\n",
        "",
    ),
)
@pytest.mark.parametrize("quote", ('"', "'"))
def test_attr_values_quoted(event_collector, attribute, quote):
    event_collector.check_events(
        f"<a b={quote}{attribute}{quote}>",
        [("starttag", "a", [("b", attribute)])],
    )


def test_attr_values_unquoted_url(event_collector):
    # URL construction stuff from RFC 1808:
    safe = "$-_.+"
    extra = "!*'(),"
    reserved = ";/?:@&="
    url = f"https://example.com:8080/path/to/file?{safe}{extra}{reserved}"
    event_collector.check_events(
        """<e a=%s>""" % url,
        [
            ("starttag", "e", [("a", url)]),
        ],
    )


def test_attr_values_unquoted(event_collector):
    # Regression test for SF patch #669683.
    event_collector.check_events(
        "<e a=rgb(1,2,3)>",
        [
            ("starttag", "e", [("a", "rgb(1,2,3)")]),
        ],
    )


def test_attr_values_entities(event_collector):
    """Substitution of entities and charrefs in attribute values"""
    # SF bug #1452246
    event_collector.check_events(
        """<a b=&lt; c=&lt;&gt; d=&lt-&gt; e='&lt; '
                            f="&xxx;" g='&#32;&#33;' h='&#500;'
                            i='x?a=b&c=d;'
                            j='&amp;#42;' k='&#38;#42;'>""",
        [
            (
                "starttag",
                "a",
                [
                    ("b", "<"),
                    ("c", "<>"),
                    ("d", "&lt->"),
                    ("e", "< "),
                    ("f", "&xxx;"),
                    ("g", " !"),
                    ("h", "&#500;"),
                    ("i", "x?a=b&c=d;"),
                    ("j", "&#42;"),
                    ("k", "&#42;"),
                ],
            )
        ],
    )


def test_convert_overrides(html_entity_collector):
    # This checks that the character and entity reference
    # conversion helpers are called at the documented times.  No
    # attempt is made to really change what the parser accepts.
    #
    html_entity_collector.check_events(
        '<a title="&ldquo;test&#x201d;">foo</a>&foobar;&#42;',
        [
            ("entityref", "convert", "ldquo"),
            ("charref", "convert", "x201d"),
            ("starttag", "a", [("title", "&ldquo;test&#x201d;")]),
            ("data", "foo"),
            ("endtag", "a"),
            ("entityref", "foobar"),
            ("entityref", "convert", "foobar"),
            ("charref", "42"),
            ("charref", "convert", "42"),
            ("codepoint", "convert", 42),
        ],
    )


def test_attr_funky_names(event_collector):
    event_collector.check_events(
        """<a a.b='v' c:d=v e-f=v>""",
        [
            ("starttag", "a", [("a.b", "v"), ("c:d", "v"), ("e-f", "v")]),
        ],
    )


def test_attr_value_ip6_url(event_collector):
    # http://www.python.org/sf/853506
    event_collector.check_events(
        (
            "<a href='http://[1080::8:800:200C:417A]/'>"
            "<a href=http://[1080::8:800:200C:417A]/>"
        ),
        [
            ("starttag", "a", [("href", "http://[1080::8:800:200C:417A]/")]),
            ("starttag", "a", [("href", "http://[1080::8:800:200C:417A]/")]),
        ],
    )


@pytest.mark.parametrize(
    "source, expected",
    (
        ("<a<a>", [("starttag", "a", []), ("starttag", "a", [])]),
        ("</a<a>", [("endtag", "a"), ("starttag", "a", [])]),
    ),
)
def test_weird_starttags(event_collector, source, expected):
    event_collector.check_events(source, expected)


def test_declaration_junk_chars(check_parse_error):
    check_parse_error("<!DOCTYPE foo $ >")


def test_get_starttag_text(event_collector):
    s = """<foobar   \n   one="1"\ttwo=2   >"""
    event_collector.check_events(
        s,
        [
            ("starttag", "foobar", [("one", "1"), ("two", "2")]),
        ],
    )


@pytest.mark.parametrize(
    "data",
    (
        "<!-- not a comment -->",
        "&not-an-entity-ref;",
        "<not a='start tag'>",
    ),
)
def test_cdata_content(cdata_event_collector, data):
    s = f"<cdata> {data} </cdata><notcdata> <!-- comment --> </notcdata>"
    cdata_event_collector.check_events(
        s,
        [
            ("starttag", "cdata", []),
            ("data", f" {data} "),
            ("endtag", "cdata"),
            ("starttag", "notcdata", []),
            ("data", " "),
            ("comment", " comment "),
            ("data", " "),
            ("endtag", "notcdata"),
        ],
    )


def test_illegal_declarations(event_collector):
    s = 'abc<!spacer type="block" height="25">def'
    event_collector.check_events(
        s,
        [
            ("data", "abc"),
            ("unknown decl", 'spacer type="block" height="25"'),
            ("data", "def"),
        ],
    )


def test_enumerated_attr_type(event_collector):
    s = "<!DOCTYPE doc [<!ATTLIST doc attr (a | b) >]>"
    event_collector.check_events(
        s,
        [
            ("decl", "DOCTYPE doc [<!ATTLIST doc attr (a | b) >]"),
        ],
    )


@pytest.fixture(scope="session")
def _sgml_input_html():
    # Read the file exactly once.
    path = pathlib.Path(__file__).parent / "sgml_input.html"
    return path.read_text(encoding="ISO-8859-1")


@pytest.fixture()
def sgml_input_html(_sgml_input_html):
    return io.StringIO(_sgml_input_html)


@pytest.mark.parametrize("chunk_size", (1, 1024, 8212))
def test_read_chunks(chunk_size, sgml_input_html):
    # SF bug #1541697, this caused sgml parser to hang
    # Just verify this code doesn't cause a hang.
    # The problem goes away if the chunk size is 8212.

    fp = sgmllib.SGMLParser()
    while 1:
        data = sgml_input_html.read(chunk_size)
        fp.feed(data)
        if len(data) != chunk_size:
            break


def test_only_decode_ascii(event_collector):
    # SF bug #1651995, make sure non-ascii character references are not decoded
    s = '<signs exclamation="&#33" copyright="&#169" quoteleft="&#8216;">'
    event_collector.check_events(
        s,
        [
            (
                "starttag",
                "signs",
                [
                    ("exclamation", "!"),
                    ("copyright", "&#169"),
                    ("quoteleft", "&#8216;"),
                ],
            ),
        ],
    )


@pytest.mark.parametrize(
    "text",
    (
        pytest.param("&#09;", id="decimal"),
        pytest.param("&#x0af9;", id="hex-lowercase-digits"),
        pytest.param("&#x0AF9;", id="hex-uppercase-digits"),
        pytest.param("&#x0af9;", id="hex-lowercase-x"),
        pytest.param("&#X0af9;", id="hex-uppercase-X"),
    ),
)
def test_numeric_character_references_positive(text):
    """Verify numeric character references can be matched."""

    assert sgmllib.charref.match(text).string == text
    assert sgmllib.charref.search(text).string == text


@pytest.mark.parametrize(
    "text",
    (
        pytest.param("&#0A;", id="decimal-only-digits-matched"),
        pytest.param("&#0४;", id="decimal-only-ascii-matched"),
        pytest.param("&#x0G;", id="hexadecimal-only-hex-digits-matched"),
        pytest.param("&#x0४;", id="hexadecimal-only-ascii-matched"),
    ),
)
def test_numeric_character_references_negative(text):
    """Verify invalid numeric character references are rejected."""

    assert sgmllib.charref.match(text) is None
    assert sgmllib.charref.search(text) is None


@pytest.mark.parametrize(
    "text",
    (
        pytest.param("aA0-_.9Zz", id="bare-lowercase-first"),
        pytest.param("Aa0-_.9zZ", id="bare-uppercase-first"),
        pytest.param("AazZ:0Aa-_.zZ9", id="xml-namespace-uppercase-first"),
        pytest.param("aAZz:0Aa-_.zZ9", id="xml-namespace-lowercase-first"),
    ),
)
def test_tagfind_positive(text):
    """Verify that tags can be matched."""

    assert sgmllib.tagfind.match(text).string == text
    assert sgmllib.tagfind.search(text).string == text


@pytest.mark.parametrize(
    "text",
    (
        pytest.param("0az", id="leading-digit"),
        pytest.param("a=z", id="symbol"),
        pytest.param("0az:az", id="namespaced-leading-digit"),
    ),
)
def test_tagfind_negative(text):
    """Verify invalid tags are rejected."""

    assert sgmllib.tagfind.match(text) != text
    assert sgmllib.tagfind.search(text) != text


def test_attrfind_trailing_dollar_sign():
    """
    Verify that a trailing dollar sign can be found in an attribute.

    Circa August 2011, Blogger wrote image tags like this:

        <img border="0" i$="true" src="http://site.invalid/img.jpg" />

    sgmllib did not recognize the "i$" attribute name,
    and this caused the "src" attribute to be lost.
    Allowing trailing dollar signs resolved this issue.

    NOTE: The dollar sign is not a part of the attribute name.
    """

    text = 'i$="true"'
    assert sgmllib.attrfind.match(text).groups() == ("i", '="true"', '"true"')
    assert sgmllib.attrfind.search(text).groups() == ("i", '="true"', '"true"')


def test_endtag_closes_innermost_matching_tag(nested_tag_collector):
    """
    Regression test: Confirm closing tags close innermost tags.

    For example:

        <a id="1"> <b> <a id="2"></a>

    The </a> must close id=2 only, leaving <b> open.
    """

    nested_tag_collector.feed('<a id="1"><b></c><a id="2"></a>')

    assert nested_tag_collector.events == [
        ("start_a", [("id", "1")]),
        ("start_b", []),
        ("unknown_endtag", "c"),
        ("start_a", [("id", "2")]),
        ("end_a",),
    ]
    assert nested_tag_collector.stack == ["a", "b"]

    # The innermost <a> (id=2) should be closed, and <b> should still be open.
    # Therefore, `end_b` should be called, not `unknown_endtag`.
    nested_tag_collector.feed("</b>")
    assert nested_tag_collector.events[-1] == ("end_b",)
    assert nested_tag_collector.stack == ["a"]


@pytest.mark.parametrize(
    "trailing_text",
    (
        " bonus",
        "/",
        "=x",
        ";",
        ",",
    ),
)
def test_endtag_with_trailing_content_still_closes_tag(
    cdata_event_collector, trailing_text
):
    """Verify that a closing tag with trailing content still closes the tag."""

    cdata_event_collector.check_events(
        f"<cdata>content</cdata{trailing_text}>after",
        [
            ("starttag", "cdata", []),
            ("data", "content"),
            ("endtag", "cdata"),
            ("data", "after"),
        ],
    )
    assert cdata_event_collector.stack == []


def test_endtag_with_no_valid_tag_name_does_not_close_open_tag(nested_tag_collector):
    """Verify invalid tag names do not close any open tags."""

    nested_tag_collector.feed("<a>content</123>after")

    assert nested_tag_collector.events == [
        ("start_a", []),
        ("unknown_endtag", "123"),
    ]
    assert nested_tag_collector.stack == ["a"]


@pytest.mark.parametrize(
    "prefix",
    (
        pytest.param('<a href="', id="starttag-unterminated-attribute"),
        pytest.param("</", id="endtag-missing-close-bracket"),
        pytest.param("<?", id="processing-instruction-missing-close"),
        pytest.param("<!--", id="comment-missing-close"),
        pytest.param("<!DOCTYPE ", id="declaration-missing-close"),
        pytest.param("<![CDATA[", id="marked-section-missing-close"),
    ),
)
def test_feed_unresolved_token_scales_cpu_time_linearly(prefix):
    """
    Verify `.feed()` doesn't exhibit quadratic CPU time usage.

    This is verified by creating a very large, incomplete token
    (like an unclosed start tag) and feeding it to the parser
    one byte at a time. The amount of CPU time required for this
    suggests whether the parser has redeveloped quadratic behavior.

    The first and last quarters of the data feed times are measured
    because linear behavior should keep their ratio close to 1.
    Having two quarters' worth of data between the measured quarters
    helps make quadratic behavior much more noticeable.
    """

    n = 60_000
    length = n - len(prefix)
    payload = prefix + ("x" * length)
    parser = sgmllib.SGMLParser()

    quarter = n // 4
    checkpoints = []
    start = time.process_time()
    for i, character in enumerate(payload, start=1):
        parser.feed(character)
        # At the end of each content quarter,
        # capture the processing time and restart the timer.
        if i % quarter == 0:
            checkpoints.append(time.process_time() - start)
            start = time.process_time()

    assert len(checkpoints) == 4
    first_quarter, last_quarter = checkpoints[0], checkpoints[-1]

    max_allowed_growth = 2.5
    # The numbers are scaled up to try to avoid close-to-zero float math problems.
    budget = (first_quarter * 10_000) * max_allowed_growth
    assert last_quarter * 10_000 <= budget, (
        f"The cost of the last quarter of feed() calls ({last_quarter:.3f}s) "
        f"exceeded {max_allowed_growth}x the cost of the first quarter "
        f"({first_quarter:.3f}s) for prefix {prefix!r}. "
        f"This suggests quadratic behavior."
    )


def test_feed_unresolved_token_peak_memory_scales_nicely():
    """
    Verify `.feed()` doesn't show a big peak memory usage constant multiplier.

    This is verified by creating a very large, incomplete token
    (like an unclosed start tag) and feeding it to the parser
    one character at a time.

    In the past, each character was concatenated each time `.feed()` is called.
    For a large input, peak memory usage was always ~2x the current input size:
    concatenation copied the existing string in memory to add a single character.

    The initial fix for quadratic CPU usage replaced string concatenation
    in favor of buffering incoming strings in a list.
    However, this caused a jump in the peak memory usage constant multiplier:
    now, in addition to the strings themselves, lots of references to the strings
    had to be created and stored in the list buffer.

    The solution was to replace the list of strings with something
    which has a resizeable internal buffer and can store the incoming data
    without the added cost of maintaining references or concatenating content.
    """

    # 200,000 should be big enough to dominate memory usage while the test runs
    # so that peak memory usage is primarily influenced by the input payload
    # and its final string-concatenation.
    n = 200_000

    prefix = '<a href="'
    length = n - len(prefix)
    payload = prefix + ("x" * length)
    parser = sgmllib.SGMLParser()

    tracemalloc.start()
    try:
        for ch in payload:
            parser.feed(ch)
        parser.close()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    # The `max_allowed_ratio` reflects how large peak memory usage can be
    # when compared to the size of the input payload.
    # As long as the input payload dominates memory usage while the test runs,
    # the string concatenation of the `SGMLParser._rawdata`
    # with the buffered, unparsed data in `._pending` should double peak usage.
    #
    # The max allowed ratio is set to 3.0 to allow for other memory use,
    # but is still lower than what was measured when a list of strings was used
    # to accumulate unparsed input data.
    max_allowed_ratio = 3.0
    budget = n * max_allowed_ratio
    assert peak <= budget, (
        f"Peak traced memory ({peak:,} bytes) exceeded "
        f"{max_allowed_ratio}x the input size ({len(payload):,} bytes) "
        "while feeding an unresolved token byte-at-a-time."
    )


# XXX These tests have been disabled by prefixing their names with
# an underscore.  The first two exercise outstanding bugs in the
# sgmllib module, and the third exhibits questionable behavior
# that needs to be carefully considered before changing it.


def _test_starttag_end_boundary(event_collector):
    event_collector.check_events("<a b='<'>", [("starttag", "a", [("b", "<")])])
    event_collector.check_events("<a b='>'>", [("starttag", "a", [("b", ">")])])


def _test_buffer_artefacts(event_collector):
    output = [("starttag", "a", [("b", "<")])]
    event_collector.check_events(["<a b='<'>"], output)
    event_collector.check_events(["<a ", "b='<'>"], output)
    event_collector.check_events(["<a b", "='<'>"], output)
    event_collector.check_events(["<a b=", "'<'>"], output)
    event_collector.check_events(["<a b='<", "'>"], output)
    event_collector.check_events(["<a b='<'", ">"], output)

    output = [("starttag", "a", [("b", ">")])]
    event_collector.check_events(["<a b='>'>"], output)
    event_collector.check_events(["<a ", "b='>'>"], output)
    event_collector.check_events(["<a b", "='>'>"], output)
    event_collector.check_events(["<a b=", "'>'>"], output)
    event_collector.check_events(["<a b='>", "'>"], output)
    event_collector.check_events(["<a b='>'", ">"], output)

    output = [("comment", "abc")]
    event_collector.check_events(["", "<!--abc-->"], output)
    event_collector.check_events(["<", "!--abc-->"], output)
    event_collector.check_events(["<!", "--abc-->"], output)
    event_collector.check_events(["<!-", "-abc-->"], output)
    event_collector.check_events(["<!--", "abc-->"], output)
    event_collector.check_events(["<!--a", "bc-->"], output)
    event_collector.check_events(["<!--ab", "c-->"], output)
    event_collector.check_events(["<!--abc", "-->"], output)
    event_collector.check_events(["<!--abc-", "->"], output)
    event_collector.check_events(["<!--abc--", ">"], output)
    event_collector.check_events(["<!--abc-->", ""], output)


def _test_starttag_junk_chars(check_parse_error):
    check_parse_error("<")
    check_parse_error("<>")
    check_parse_error("</$>")
    check_parse_error("</")
    check_parse_error("</a")
    check_parse_error("<$")
    check_parse_error("<$>")
    check_parse_error("<!")
    check_parse_error("<a $>")
    check_parse_error("<a")
    check_parse_error("<a foo='bar'")
    check_parse_error("<a foo='bar")
    check_parse_error("<a foo='>'")
    check_parse_error("<a foo='>")
    check_parse_error("<a foo=>")
