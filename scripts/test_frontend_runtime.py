import reflex as rx

import unittest
from pathlib import Path

from reflex.utils.prerequisites import get_web_dir
from reflex_base import constants
from rxconfig import FrontendRuntimePlugin, config


class FrontendRuntimeTests(unittest.TestCase):
    """Read-only checks to run after the platform's normal recompile."""

    def test_registered_plugin(self):
        self.assertTrue(issubclass(FrontendRuntimePlugin, rx.plugins.Plugin))
        self.assertTrue(
            any(
                isinstance(plugin, FrontendRuntimePlugin)
                for plugin in config.plugins
            )
        )

    def test_generated_configs_excluded(self):
        assets = dict(FrontendRuntimePlugin().get_static_assets())
        for generated in (
            Path("react-router.config.js"),
            Path("postcss.config.js"),
            Path("app/entry.client.js"),
        ):
            with self.subTest(generated=str(generated)):
                self.assertNotIn(generated, assets)

    def test_compiled_postcss_preserves_tailwind_plugin(self):
        postcss = (get_web_dir() / "postcss.config.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('"@tailwindcss/postcss"', postcss)
        self.assertNotIn('"postcss-import"', postcss)

    def test_all_static_templates_match(self):
        web = get_web_dir()
        assets = dict(FrontendRuntimePlugin().get_static_assets())
        self.assertIn(Path("utils/context-registry.js"), assets)
        self.assertIn(Path("utils/state.js"), assets)
        self.assertIn(Path("app/routes.js"), assets)
        for relative, expected in assets.items():
            with self.subTest(template=str(relative)):
                self.assertEqual(
                    (web / relative).read_text(encoding="utf-8"), expected
                )
        entry = Path("app/entry.client.js")
        self.assertEqual(
            (web / entry).read_text(encoding="utf-8"),
            (constants.Templates.Dirs.WEB_TEMPLATE / entry).read_text(
                encoding="utf-8"
            ),
        )

    def test_root_and_context_exports(self):
        web = get_web_dir()
        root = web / "app/root.jsx"
        self.assertTrue(
            root.is_file(), "The compiler must emit the root wrapper"
        )
        self.assertTrue(root.read_text(encoding="utf-8").strip())
        registry = (web / "utils/context-registry.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("export const StateStoreContext", registry)
        self.assertIn("export function useStateContext(", registry)

    def test_student_project_compiled_modules(self):
        web = get_web_dir()
        student = web / "app_components/UniFlow_/components/student.jsx"
        code = student.read_text(encoding="utf-8")
        self.assertIn("useStateContext", code)
        self.assertNotIn("pyOr", code)
        routes = list((web / "app/routes").rglob("*projects*"))
        self.assertTrue(routes, "Student project routes must be emitted")
        for route in routes:
            if route.is_file() and route.suffix in {".js", ".jsx"}:
                with self.subTest(route=str(route)):
                    self.assertNotIn("pyOr", route.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
