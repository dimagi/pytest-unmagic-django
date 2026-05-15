"""pytest-django interop for pytest-unmagic.

Registers a pytest_itemcollected hook that surfaces @use'd pytest-fixture
names on the test item so pytest-django can see them at collection time and
arrange DB setup accordingly.
"""

# Name registered by pytest-django's pytest11 entry point
_PYTEST_DJANGO_PLUGIN_NAME = "django"


def _is_pytest_fixture_id(fid):
    # PytestFixture stores a plain str as _id; UnmagicFixture stores a
    # _UnmagicID (str subclass with identity equality) which pytest-django
    # does not look for. `type(x) is str` — not `isinstance` — discriminates.
    return type(fid) is str


def pytest_itemcollected(item):
    """Surface @use'd pytest-fixture names on the collected item.

    pytest-django decides at collection time whether to set up the test
    database by scanning each item's fixturenames. Because unmagic resolves
    @use'd fixtures lazily via getfixturevalue, those names are absent from
    fixturenames at collection time.

    For every pytest-fixture name in the item's unmagic_fixtures list,
    append it to item.fixturenames if not already present.
    """
    if not item.config.pluginmanager.hasplugin(_PYTEST_DJANGO_PLUGIN_NAME):
        return
    fixtures = getattr(item.obj, "unmagic_fixtures", None)
    if not fixtures:
        return
    names = item.fixturenames
    for fix in fixtures:
        fid = getattr(fix, "_id", None)
        if _is_pytest_fixture_id(fid) and fid not in names:
            names.append(fid)
