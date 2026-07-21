import re

import pytest

import feedparser.sgmllib as sgmllib


@pytest.fixture
def check_parse_error():
    def checker(source: str):
        parser = EventCollector()
        with pytest.raises(sgmllib.SGMLParseError):
            parser.feed(source)
            parser.close()

    yield checker


@pytest.fixture
def event_collector():
    return EventCollector()


@pytest.fixture
def cdata_event_collector():
    return CDATAEventCollector()


@pytest.fixture
def html_entity_collector():
    return HTMLEntityCollector()


class EventCollector(sgmllib.SGMLParser):
    def check_events(self, source, expected_events):
        self._consume_source(source)
        self._normalize_events()
        assert self.events == expected_events

    def _normalize_events(self):
        # Normalize the list of events so that buffer artifacts don't
        # separate runs of contiguous characters.
        normalized_events = []
        previous_type = None
        for event in self.events:
            current_type = event[0]
            if current_type == previous_type == "data":
                normalized_events[-1] = ("data", normalized_events[-1][1] + event[1])
            else:
                normalized_events.append(event)
            previous_type = current_type
        self.events = normalized_events

    def _consume_source(self, source):
        for s in source:
            self.feed(s)
        self.close()

    def __init__(self) -> None:
        self.events = []
        super().__init__()

    # structure markup

    def unknown_starttag(self, tag, attrs):
        self.events.append(("starttag", tag, attrs))

    def unknown_endtag(self, tag):
        self.events.append(("endtag", tag))

    # all other markup

    def handle_comment(self, data):
        self.events.append(("comment", data))

    def handle_charref(self, name):
        self.events.append(("charref", name))

    def handle_data(self, data):
        self.events.append(("data", data))

    def handle_decl(self, decl):
        self.events.append(("decl", decl))

    def handle_entityref(self, name):
        self.events.append(("entityref", name))

    def handle_pi(self, data):
        self.events.append(("pi", data))

    def unknown_decl(self, data):
        self.events.append(("unknown decl", data))


class CDATAEventCollector(EventCollector):
    def start_cdata(self, attrs):
        self.events.append(("starttag", "cdata", attrs))
        self.setliteral()


class HTMLEntityCollector(EventCollector):

    entity_or_charref = re.compile(
        "(?:&([a-zA-Z][-.a-zA-Z0-9]*)|&#(x[0-9a-zA-Z]+|[0-9]+))(;?)"
    )

    def convert_charref(self, name):
        self.events.append(("charref", "convert", name))
        if name[0] != "x":
            return super().convert_charref(name)

    def convert_codepoint(self, codepoint):
        self.events.append(("codepoint", "convert", codepoint))
        super().convert_codepoint(codepoint)

    def convert_entityref(self, name):
        self.events.append(("entityref", "convert", name))
        return super().convert_entityref(name)

    # These to record that they were called, then pass the call along
    # to the default implementation so that its actions can be
    # recorded.

    def handle_charref(self, name):
        self.events.append(("charref", name))
        sgmllib.SGMLParser.handle_charref(self, name)

    def handle_entityref(self, name):
        self.events.append(("entityref", name))
        sgmllib.SGMLParser.handle_entityref(self, name)
