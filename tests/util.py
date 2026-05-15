from contextlib import contextmanager
from unittest.mock import patch

import _pytest.pytester as _pytester
from unmagic import fixture
from unmagic.scope import get_active, get_request, set_active


@fixture
def django_tester():
    with patch.object(_pytester, "main", unmagic_inactive()(_pytester.main)):
        pytester = get_request().getfixturevalue("pytester")
        pytester.makeini(
            "[pytest]\n"
            "DJANGO_SETTINGS_MODULE = tests.django_app.settings\n"
        )
        yield pytester


@contextmanager
def unmagic_inactive():
    obj = get_active()
    set_active(None)
    try:
        yield
    finally:
        set_active(obj)
