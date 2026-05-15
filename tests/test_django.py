"""Integration tests for pytest-unmagic-django.

Each test that drives a sub-pytest uses the `django_tester` fixture
(from tests.util) which sets up pytester with DJANGO_SETTINGS_MODULE
pointing at tests.django_app.settings.
"""
import textwrap

from unmagic import use

from .util import django_tester


@use(django_tester)
def test_use_db_triggers_pytest_django_setup():
    tester = django_tester()
    tester.makepyfile(textwrap.dedent("""
        from unmagic import use
        from tests.django_app.models import Thing

        @use('db')
        def test_creates_row():
            Thing.objects.create(name='x')
            assert Thing.objects.count() == 1
    """))
    result = tester.runpytest("-q")
    result.assert_outcomes(passed=1)


@use(django_tester)
def test_use_db_via_nested_unmagic_fixture():
    """A user-defined unmagic fixture that declares @use('db') in its own
    decorator chain should still trigger DB setup when applied to a test that
    does not itself declare 'db'."""
    tester = django_tester()
    tester.makepyfile(textwrap.dedent("""
        from unmagic import fixture, use
        from tests.django_app.models import Thing

        @use('db')
        @fixture
        def seeded():
            Thing.objects.create(name='seed')
            yield

        @use(seeded)
        def test_reads_seed():
            assert Thing.objects.filter(name='seed').exists()
    """))
    result = tester.runpytest("-q")
    result.assert_outcomes(passed=1)


@use(django_tester)
def test_inline_db_without_declaration_raises():
    """The guard raises when 'db' is resolved inline without @use declaration.

    Without the guard, pytest-django's behaviour depends on the database
    backend. For SQLite :memory: (used here) there is no persistent real
    database, so lazy db() resolution happens to work. For a real database
    (e.g. PostgreSQL), the missing declaration means pytest-django's
    database blocker is still active, leading to an obscure error from
    inside pytest-django or, in some configurations, access to the real
    database, and the test passes silently.

    The guard catches this consistently across all backends by raising at
    fixture-setup time before any database access occurs.

    Stdout assertions are used rather than outcome counters because pytest
    surfaces setup-time failures differently across versions.
    """
    tester = django_tester()
    tester.makepyfile(textwrap.dedent("""
        from unmagic import fixture, use
        from unmagic.fixtures import UnmagicFixture
        from tests.django_app.models import Thing

        db = UnmagicFixture.create('db')

        @fixture
        def stealth_db():
            db()  # inline resolution; never declared via @use
            print("STEALTH_DB_RAN")
            yield

        @use(stealth_db)
        def test_inline():
            print("TEST_BODY_RAN")
            Thing.objects.create(name='x')
    """))
    result = tester.runpytest("-q")
    assert result.ret != 0
    result.stdout.fnmatch_lines([
        "*RuntimeError*",
        "*pytest-django fixture 'db'*",
        "*not declared*",
    ])
    result.stdout.no_fnmatch_line("*STEALTH_DB_RAN*")
    result.stdout.no_fnmatch_line("*TEST_BODY_RAN*")


@use(django_tester)
def test_django_db_marker_bypasses_guard():
    """A test with @pytest.mark.django_db does not need @use('db')."""
    tester = django_tester()
    tester.makepyfile(textwrap.dedent("""
        import pytest
        from unmagic.fixtures import UnmagicFixture
        from tests.django_app.models import Thing

        db = UnmagicFixture.create('db')

        @pytest.mark.django_db
        def test_marked():
            db()
            Thing.objects.create(name='x')
            assert Thing.objects.count() == 1
    """))
    result = tester.runpytest("-q")
    result.assert_outcomes(passed=1)


@use(django_tester)
def test_declared_db_does_not_trip_guard():
    """When 'db' is declared via @use, fixture resolution must succeed."""
    tester = django_tester()
    tester.makepyfile(textwrap.dedent("""
        from unmagic import use
        from tests.django_app.models import Thing

        @use('db')
        def test_ok():
            Thing.objects.create(name='ok')
            assert Thing.objects.count() == 1
    """))
    result = tester.runpytest("-q")
    result.assert_outcomes(passed=1)


@use(django_tester)
def test_session_scoped_db_fixture_does_not_crash_guard():
    """Guard must not crash when a session-scoped fixture in _DB_FIXTURE_NAMES
    is being set up.

    Session nodes lack a fixturenames attribute, so accessing it in the guard
    raises AttributeError. The fix skips the guard for non-item nodes.

    This models the real-world case of pytest-django's live_server fixture,
    which is session-scoped and is guarded by _DB_FIXTURE_NAMES.
    """
    tester = django_tester()
    tester.makeconftest(textwrap.dedent("""
        import pytest
        import unmagic_django

        @pytest.fixture(scope='session')
        def session_db_server():
            yield 'server'

        unmagic_django._DB_FIXTURE_NAMES = (
            unmagic_django._DB_FIXTURE_NAMES | {'session_db_server'}
        )
    """))
    tester.makepyfile(textwrap.dedent("""
        from unmagic import use

        @use('session_db_server')
        def test_uses_session_fixture():
            pass
    """))
    result = tester.runpytest("-q")
    result.assert_outcomes(passed=1)
