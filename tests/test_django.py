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
def test_inline_db_without_declaration():
    """Verify pytest-django's native behavior when the 'db' fixture is
    resolved inline (via UnmagicFixture.create / getfixturevalue) without
    being declared via @use or a django_db marker.

    The observed behaviour depends on the database backend. For SQLite
    :memory: (used here) there is no persistent real database, so lazy
    db() resolution happens to work. For a real database (e.g.
    PostgreSQL), the missing declaration means pytest-django's database
    blocker is still active, leading to an obscure error from inside
    pytest-django or, in some configurations, access to the real
    database, and the test passes silently. This means the declaration
    requirement is not enforced without a guard.
    """
    tester = django_tester()
    tester.makepyfile(textwrap.dedent("""
        from unmagic import fixture, use
        from unmagic.fixtures import UnmagicFixture
        from tests.django_app.models import Thing

        # Resolve the pytest-django 'db' fixture from inside the body
        # without declaring it via @use anywhere in the chain.
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
    result = tester.runpytest("-q", "-s")
    # pytest-django silently succeeds: both fixture and test body run.
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*STEALTH_DB_RAN*", "*TEST_BODY_RAN*"])


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
