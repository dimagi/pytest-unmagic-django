"""pytest-django interop for pytest-unmagic.

Registers hooks to integrate pytest-django's database setup with unmagic's
lazy fixture resolution:

- pytest_itemcollected: surfaces @use'd pytest-fixture names on the test item
  so pytest-django sees them at collection time and arranges DB setup.
- pytest_fixture_setup: guards against DB fixtures being set up for a test
  that never declared them, raising a clear error instead of silently passing.
"""

import pytest

# Name registered by pytest-django's pytest11 entry point
_PYTEST_DJANGO_PLUGIN_NAME = "django"

# pytest-django fixture names whose setup implies the test DB must have been
# declared. Matches the set pytest-django checks at collection time.
_DB_FIXTURE_NAMES = frozenset({
    "db",
    "transactional_db",
    "django_db_reset_sequences",
    "django_db_serialized_rollback",
    "live_server",
})


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


@pytest.hookimpl(tryfirst=True)
def pytest_fixture_setup(fixturedef, request):
    """Guard against undeclared pytest-django DB fixture access.

    If a DB fixture is being set up for a test that never declared it via
    @use or a django_db marker, raise a clear error. Without this guard,
    pytest-django silently sets up the database on demand, allowing the
    @use declaration requirement to be bypassed undetected.
    """
    if fixturedef.argname not in _DB_FIXTURE_NAMES:
        return
    if not request.config.pluginmanager.hasplugin(_PYTEST_DJANGO_PLUGIN_NAME):
        return
    node = request.node
    if not hasattr(node, "fixturenames"):
        return
    if fixturedef.argname in node.fixturenames:
        return
    if node.get_closest_marker("django_db") is not None:
        return
    raise RuntimeError(
        f"pytest-django fixture {fixturedef.argname!r} is being set up, but "
        f"was not declared via @use({fixturedef.argname!r}) on the test or on "
        f"a fixture in its @use chain, and no @pytest.mark.django_db marker "
        f"is present. Declare the dependency to make DB setup explicit."
    )
