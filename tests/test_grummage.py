import os
import sys
import types
import unittest
from unittest import mock


def install_textual_stubs():
    textual = types.ModuleType("textual")
    textual.work = lambda *args, **kwargs: (lambda func: func)

    textual_app = types.ModuleType("textual.app")
    textual_containers = types.ModuleType("textual.containers")
    textual_screen = types.ModuleType("textual.screen")
    textual_widgets = types.ModuleType("textual.widgets")
    textual_worker = types.ModuleType("textual.worker")

    class DummyBase:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyApp(DummyBase):
        pass

    textual_app.App = DummyApp
    textual_containers.Container = DummyBase
    textual_containers.Horizontal = DummyBase
    textual_containers.VerticalScroll = DummyBase
    textual_containers.Vertical = DummyBase
    textual_screen.ModalScreen = DummyBase
    textual_widgets.Tree = DummyBase
    textual_widgets.Footer = DummyBase
    textual_widgets.Static = DummyBase
    textual_widgets.Label = DummyBase
    textual_widgets.LoadingIndicator = DummyBase
    textual_widgets.Input = DummyBase
    textual_widgets.Markdown = DummyBase
    textual_worker.get_current_worker = lambda: None

    sys.modules.setdefault("textual", textual)
    sys.modules.setdefault("textual.app", textual_app)
    sys.modules.setdefault("textual.containers", textual_containers)
    sys.modules.setdefault("textual.screen", textual_screen)
    sys.modules.setdefault("textual.widgets", textual_widgets)
    sys.modules.setdefault("textual.worker", textual_worker)


install_textual_stubs()

import grummage


class FormatUrlsAsMarkdownTests(unittest.TestCase):
    def test_plain_urls_are_converted_when_markdown_link_already_exists(self):
        text = "Docs: [existing](https://example.com/docs) and https://example.com/raw"
        converted = grummage.format_urls_as_markdown(text)
        self.assertIn("[existing](https://example.com/docs)", converted)
        self.assertIn("[https://example.com/raw](https://example.com/raw)", converted)


class IsGrypeInstalledTests(unittest.TestCase):
    def test_missing_path_does_not_crash(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch("grummage.shutil.which", return_value=None):
                self.assertFalse(grummage.is_grype_installed())


class ResolveGrypeReleaseAssetTests(unittest.TestCase):
    def test_linux_amd64_archive_name(self):
        archive, checksums, binary = grummage.resolve_grype_release_asset(
            "0.111.0",
            system_name="Linux",
            machine_name="x86_64",
        )
        self.assertEqual(archive, "grype_0.111.0_linux_amd64.tar.gz")
        self.assertEqual(checksums, "grype_0.111.0_checksums.txt")
        self.assertEqual(binary, "grype")

    def test_unsupported_platform_raises(self):
        with self.assertRaises(RuntimeError):
            grummage.resolve_grype_release_asset(
                "0.111.0",
                system_name="Linux",
                machine_name="sparc64",
            )


class AddDirectoryToPathTests(unittest.TestCase):
    def test_adds_missing_directory_to_current_process_path(self):
        with mock.patch("grummage.os.path.isdir", return_value=True):
            initial_path = os.pathsep.join(["/usr/bin", "/bin"])
            with mock.patch.dict("grummage.os.environ", {"PATH": initial_path}, clear=True):
                grummage.add_directory_to_path("/home/test/.local/bin")
                self.assertEqual(
                    grummage.os.environ["PATH"],
                    os.pathsep.join(["/home/test/.local/bin", "/usr/bin", "/bin"]),
                )

    def test_ignores_directory_already_in_path(self):
        with mock.patch("grummage.os.path.isdir", return_value=True):
            existing_path = os.pathsep.join(["/home/test/.local/bin", "/usr/bin", "/bin"])
            with mock.patch.dict(
                "grummage.os.environ",
                {"PATH": existing_path},
                clear=True,
            ):
                grummage.add_directory_to_path("/home/test/.local/bin")
                self.assertEqual(
                    grummage.os.environ["PATH"],
                    existing_path,
                )


class OpenDebugLogTests(unittest.TestCase):
    def test_invalid_debug_log_path_does_not_raise(self):
        with mock.patch("builtins.open", side_effect=OSError("permission denied")):
            self.assertIsNone(grummage.open_debug_log("/root/forbidden.log"))


class RunGrypeAnalysisTests(unittest.TestCase):
    def test_temp_file_is_cleaned_up_when_subprocess_raises(self):
        app = grummage.Grummage()
        app.app = mock.Mock()
        app.update_loading_status = mock.Mock()
        app.debug_log = mock.Mock()
        app.notify = mock.Mock()
        app.pop_screen = mock.Mock()
        app.on_grype_complete = mock.Mock()

        temp_context = mock.MagicMock()
        temp_file = mock.MagicMock()
        temp_file.name = "/tmp/grummage-test.json"
        temp_context.__enter__.return_value = temp_file
        temp_context.__exit__.return_value = False

        with mock.patch("grummage.tempfile.NamedTemporaryFile", return_value=temp_context):
            with mock.patch("grummage.subprocess.run", side_effect=FileNotFoundError("grype missing")):
                with mock.patch("grummage.os.path.exists", return_value=True):
                    with mock.patch("grummage.os.unlink") as unlink_mock:
                        app.run_grype_analysis({"sbom": "data"})

        unlink_mock.assert_called_once_with("/tmp/grummage-test.json")
        app.app.call_from_thread.assert_any_call(app.update_loading_status, "Error running grype")
        app.app.call_from_thread.assert_any_call(
            app.notify,
            "Error running grype: grype missing",
            severity="error",
        )
        app.app.call_from_thread.assert_any_call(app.pop_screen)
        app.on_grype_complete.assert_not_called()


class OnKeyTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_search_binding_keys_do_not_trigger_duplicate_actions(self):
        app = grummage.Grummage()
        app.load_tree_by_package_name = mock.Mock()
        app.load_tree_by_type = mock.Mock()
        app.load_tree_by_vulnerability = mock.Mock()
        app.load_tree_by_severity = mock.Mock()
        app.explain_vulnerability_worker = mock.Mock()
        app.status_bar = mock.Mock()
        app.notify = mock.Mock()
        app.search_results = []
        app.selected_vuln_id = "CVE-2026-0001"
        app.selected_package_name = "demo"
        app.selected_package_version = "1.0"
        app.detailed_text = "details"

        for key in ("p", "t", "v", "s", "e"):
            with self.subTest(key=key):
                event = types.SimpleNamespace(key=key)
                await app.on_key(event)

        app.load_tree_by_package_name.assert_not_called()
        app.load_tree_by_type.assert_not_called()
        app.load_tree_by_vulnerability.assert_not_called()
        app.load_tree_by_severity.assert_not_called()
        app.explain_vulnerability_worker.assert_not_called()
        app.status_bar.update.assert_not_called()
        app.notify.assert_not_called()

    async def test_search_navigation_keys_are_still_handled(self):
        app = grummage.Grummage()
        app.find_next = mock.Mock()
        app.find_previous = mock.Mock()
        app.notify = mock.Mock()
        app.search_results = ["match"]

        await app.on_key(types.SimpleNamespace(key="n"))
        await app.on_key(types.SimpleNamespace(key="N"))

        app.find_next.assert_called_once_with()
        app.find_previous.assert_called_once_with()
        app.notify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
