import importlib
import pkgutil
import unittest

import pyromax


class PackageImportTest(unittest.TestCase):
    def test_every_library_module_imports(self) -> None:
        failures: list[str] = []
        optional_modules = {
            "pyromax.fsm.storage.pymongo": "pymongo",
            "pyromax.fsm.storage.redis": "redis",
        }
        modules = sorted(
            module.name
            for module in pkgutil.walk_packages(pyromax.__path__, pyromax.__name__ + ".")
        )

        for module_name in modules:
            try:
                importlib.import_module(module_name)
            except ModuleNotFoundError as error:
                if optional_modules.get(module_name) == error.name:
                    continue
                failures.append(f"{module_name}: {type(error).__name__}: {error}")
            except Exception as error:  # pragma: no cover - assertion reports module and cause
                failures.append(f"{module_name}: {type(error).__name__}: {error}")

        self.assertGreater(len(modules), 100)
        self.assertEqual(failures, [], "Module import failures:\n" + "\n".join(failures))
