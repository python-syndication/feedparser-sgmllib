import io
import pathlib

import pytest

import feedparser.sgmllib as sgmllib


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
