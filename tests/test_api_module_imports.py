import importlib
import pkgutil

from django.test import SimpleTestCase


class ApiModuleImportTests(SimpleTestCase):
    def test_import_all_domain_modules(self):
        import api.domains as package

        modules = [name for _, name, _ in pkgutil.iter_modules(package.__path__)]
        self.assertTrue(modules)
        importlib.import_module("api.domains")
        for name in modules:
            with self.subTest(module=name):
                importlib.import_module(f"api.domains.{name}")

    def test_import_all_service_modules(self):
        import api.services as package

        modules = [name for _, name, _ in pkgutil.iter_modules(package.__path__)]
        self.assertTrue(modules)
        importlib.import_module("api.services")
        for name in modules:
            with self.subTest(module=name):
                importlib.import_module(f"api.services.{name}")

    def test_import_all_view_modules(self):
        import api.views as package

        modules = [name for _, name, _ in pkgutil.iter_modules(package.__path__)]
        self.assertTrue(modules)
        importlib.import_module("api.views")
        for name in modules:
            with self.subTest(module=name):
                importlib.import_module(f"api.views.{name}")
