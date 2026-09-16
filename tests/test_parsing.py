"""
Tests for the preference-parsing functions in update_betterfox.py.

Run with:
    pip install -r requirements-dev.txt
    pytest tests/

Some tests below are marked xfail. These document known limitations in
the current regex-based parser rather than hiding them. They are not
meant to be silently "fixed" by tweaking the test to match whatever the
regex happens to do — they exist so a future parser rewrite has a
concrete list of real-world cases to verify against, and so a change
that accidentally fixes one xfail while breaking something else gets
noticed immediately.
"""
import pytest

from update_betterfox import parse_pref_names, parse_prefs, diff_prefs


# ---------------------------------------------------------------------------
# parse_pref_names
# ---------------------------------------------------------------------------

def test_parse_pref_names_basic():
    content = '''
    user_pref("browser.foo.enabled", true);
    user_pref("network.bar.timeout", 500);
    user_pref("privacy.resistFingerprinting", false);
    '''
    names = parse_pref_names(content)
    assert names == {
        "browser.foo.enabled",
        "network.bar.timeout",
        "privacy.resistFingerprinting",
    }


def test_parse_pref_names_empty_content():
    assert parse_pref_names("") == set()


def test_parse_pref_names_ignores_non_pref_lines():
    content = '''
    // Just a comment, no prefs here
    /* Block comment */
    some_random_line_that_is_not_a_pref
    user_pref("real.pref", true);
    '''
    assert parse_pref_names(content) == {"real.pref"}


def test_parse_pref_names_duplicate_entries():
    # A set naturally collapses duplicate names — fine here, since this
    # function only reports *which* prefs exist, not their values or how
    # many times each appears.
    content = '''
    user_pref("dup.pref", true);
    user_pref("dup.pref", false);
    '''
    assert parse_pref_names(content) == {"dup.pref"}


@pytest.mark.xfail(reason=(
    "Known limitation: the regex matches user_pref(...) anywhere in the "
    "text, including inside a // comment, so a commented-out pref is "
    "incorrectly treated as active. Fixing this needs line-aware "
    "parsing rather than a text-wide regex. See project code review "
    "notes on parser fragility."
))
def test_commented_out_pref_is_not_counted():
    content = '// user_pref("should.not.count", true);'
    assert parse_pref_names(content) == set()


# ---------------------------------------------------------------------------
# parse_prefs (name -> value)
# ---------------------------------------------------------------------------

def test_parse_prefs_basic_values():
    content = '''
    user_pref("browser.foo.enabled", true);
    user_pref("network.bar.timeout", 500);
    user_pref("browser.name", "value");
    '''
    prefs = parse_prefs(content)
    assert prefs["browser.foo.enabled"] == "true"
    assert prefs["network.bar.timeout"] == "500"
    assert prefs["browser.name"] == '"value"'


def test_parse_prefs_duplicate_last_wins():
    # dict(re.findall(...)) keeps the LAST match for a repeated key. This
    # pins down current behaviour explicitly — the code review flagged
    # that duplicate user_pref() entries silently collapse, and pref
    # ordering can matter in Firefox. If this behaviour is ever changed
    # (e.g. keep the first match instead, or warn on duplicates), this
    # test is the first thing that should be updated to match.
    content = '''
    user_pref("dup.pref", "first");
    user_pref("dup.pref", "second");
    '''
    prefs = parse_prefs(content)
    assert prefs["dup.pref"] == '"second"'


@pytest.mark.xfail(reason=(
    "Known limitation: the value regex stops at the first ')', so a "
    "value containing parentheses (e.g. inside a quoted string) gets "
    "truncated incorrectly. See project code review notes on parser "
    "fragility."
))
def test_value_containing_parentheses():
    content = 'user_pref("some.pref", "a value (with parens) here");'
    prefs = parse_prefs(content)
    assert prefs["some.pref"] == '"a value (with parens) here"'


def test_value_with_escaped_quotes():
    # Turns out this one actually works correctly with the current regex —
    # confirmed by running the suite, this was NOT a real limitation.
    # The value-capture group [^)]+ doesn't care about quotes at all, so
    # backslash-escaped quotes inside the value pass through as plain
    # characters with no special handling needed. Kept as a real test
    # (not xfail) so a future regex change that breaks this gets caught.
    content = r'user_pref("some.pref", "a \"quoted\" value");'
    prefs = parse_prefs(content)
    assert prefs["some.pref"] == r'"a \"quoted\" value"'


# ---------------------------------------------------------------------------
# diff_prefs
# ---------------------------------------------------------------------------

def test_diff_prefs_added_changed_removed():
    old = '''
    user_pref("kept.same", true);
    user_pref("will.change", "old");
    user_pref("will.be.removed", true);
    '''
    new = '''
    user_pref("kept.same", true);
    user_pref("will.change", "new");
    user_pref("newly.added", 42);
    '''
    diff = diff_prefs(old, new)

    assert diff["added"] == {"newly.added": "42"}
    assert diff["removed"] == {"will.be.removed": "true"}
    assert diff["changed"] == {
        "will.change": {"old": '"old"', "new": '"new"'}
    }
    assert "kept.same" not in diff["added"]
    assert "kept.same" not in diff["removed"]
    assert "kept.same" not in diff["changed"]


def test_diff_prefs_no_changes():
    content = 'user_pref("same.pref", true);'
    diff = diff_prefs(content, content)
    assert diff["added"] == {}
    assert diff["removed"] == {}
    assert diff["changed"] == {}


def test_diff_prefs_empty_old_content():
    # Simulates a first-ever sync, where there's no existing user.js to
    # diff against — every pref in the new content should show as "added".
    new = '''
    user_pref("first.pref", true);
    user_pref("second.pref", false);
    '''
    diff = diff_prefs("", new)
    assert set(diff["added"].keys()) == {"first.pref", "second.pref"}
    assert diff["removed"] == {}
    assert diff["changed"] == {}