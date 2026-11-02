from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def test_deployment_lock_contains_every_direct_dependency():
    backend = Path(__file__).resolve().parents[1]
    def requirements(name):
        result = {}
        for line in (backend / name).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                item = Requirement(line)
                result[canonicalize_name(item.name)] = str(item.specifier)
        return result
    source = requirements('requirements.txt')
    locked = requirements('requirements.lock')
    assert {name: locked.get(name) for name in source} == source
