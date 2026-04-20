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


if __name__ == "__main__":
    unittest.main()
