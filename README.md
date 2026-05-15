pytest-unmagic-django
=====================

**pytest-django support for pytest-unmagic**

pytest-unmagic-django bridges [pytest-unmagic](https://github.com/dimagi/pytest-unmagic)
and [pytest-django](https://pytest-django.readthedocs.io/) so that tests
using unmagic fixtures for database access work correctly with
pytest-django.


Installation
------------

```sh
pip install pytest-unmagic-django
```

Both `pytest-unmagic` and `pytest-django` are installed automatically as
dependencies. Django itself must be installed separately.


Usage
-----

### Declaring database access

Use `@use('db')` (or another pytest-django DB fixture) on a test or on a
fixture in its chain to declare that the test needs database access:

```python
from unmagic import use

@use('db')
def test_creates_record():
    MyModel.objects.create(name='example')
    assert MyModel.objects.count() == 1
```

The declaration is required. Without it, the guard in
pytest-unmagic-django raises a `RuntimeError` if a DB fixture is set up
without being declared, rather than silently allowing access.


### Fixtures that need database access

Apply `@use('db')` to a fixture that accesses the database. Any test
that uses the fixture will have DB access set up automatically — the
test itself does not need its own `@use('db')`:

```python
from unmagic import fixture, use

@use('db')
@fixture
def seeded_person():
    person = Person.objects.create(name='Ada')
    yield person

@use(seeded_person)
def test_person_name():
    assert seeded_person().name == 'Ada'
```


### Chaining fixtures

When multiple fixtures form a dependency chain, declare `@use ('db')`
only on the fixture that directly accesses the database.
pytest-unmagic-django walks the full `@use` chain at collection time,
so the declaration propagates up to the test automatically:

```python
from unmagic import fixture, use

@use('db')
@fixture
def author():
    yield Person.objects.create(name='Daedalus')

@use(author)
@fixture
def article():
    yield Article.objects.create(title='On flight', author=author())

@use(article)
def test_article_author():
    assert article().author.name == 'Daedalus'
```


### Transactional tests

All pytest-django DB fixtures are supported. Use `'transactional_db'`
for tests that need real transactions:

```python
from unmagic import use

@use('transactional_db')
def test_with_real_transactions():
    ...
```


Running the tests
-----------------

```sh
cd path/to/pytest-unmagic-django
pip install -e ".[test]"
pytest
```
