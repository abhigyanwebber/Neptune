import pytest

from core.registry.dependency_resolution import (
    DependencyCycleError,
    UnresolvedDependencyError,
    resolve_dependencies,
)


def test_resolve_dependencies_simple_chain():
    # browser tool depends on docker resource; docker depends on nothing.
    depends_on_map = {
        "browser": ["docker"],
        "docker": [],
    }
    order = resolve_dependencies("browser", depends_on_map)
    assert order == ["docker", "browser"]


def test_resolve_dependencies_diamond():
    #      terminal
    #      /      \
    #  docker    local_fs
    #      \      /
    #     (no shared dep, just two direct deps)
    depends_on_map = {
        "terminal": ["docker", "local_fs"],
        "docker": [],
        "local_fs": [],
    }
    order = resolve_dependencies("terminal", depends_on_map)
    assert order.index("docker") < order.index("terminal")
    assert order.index("local_fs") < order.index("terminal")
    assert order[-1] == "terminal"


def test_resolve_dependencies_detects_cycle():
    depends_on_map = {
        "a": ["b"],
        "b": ["c"],
        "c": ["a"],
    }
    with pytest.raises(DependencyCycleError):
        resolve_dependencies("a", depends_on_map)


def test_resolve_dependencies_unknown_entry_raises_by_default():
    depends_on_map = {"browser": ["docker"]}
    with pytest.raises(UnresolvedDependencyError):
        resolve_dependencies("browser", depends_on_map)


def test_resolve_dependencies_unknown_entry_allowed_when_not_required():
    depends_on_map = {"browser": ["docker"]}
    order = resolve_dependencies("browser", depends_on_map, require_known=False)
    assert order == ["docker", "browser"]


def test_resolve_dependencies_no_dependencies():
    depends_on_map = {"groq": []}
    assert resolve_dependencies("groq", depends_on_map) == ["groq"]
