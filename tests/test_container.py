import pytest
from app.container import DependencyContainer


def test_container_resolves_singleton_factory():
    container = DependencyContainer()
    calls = []
    container.register_factory("service", lambda c: calls.append(1) or object())
    first = container.resolve("service")
    second = container.resolve("service")
    assert first is second
    assert len(calls) == 1


def test_missing_dependency_is_explicit():
    with pytest.raises(KeyError):
        DependencyContainer().resolve("missing")
