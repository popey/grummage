#!/usr/bin/env python
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

from textual import work
from textual.app import App
from textual.containers import Container, Horizontal, VerticalScroll, Vertical
from textual.screen import ModalScreen
from textual.widgets import Tree, Footer, Static, Label, LoadingIndicator, Input
from textual.widgets import Markdown
from textual.worker import get_current_worker

GRYPE_RELEASES_API = "https://api.github.com/repos/anchore/grype/releases/latest"
GRYPE_RELEASES_DOWNLOAD = "https://github.com/anchore/grype/releases/download"
GRYPE_USER_AGENT = "grummage"


def format_urls_as_markdown(text):
    """Convert plain URLs in text to markdown links without double-wrapping markdown links."""
    markdown_links = []

    def protect_markdown_link(match):
        markdown_links.append(match.group(0))
        return f"__GRUMMAGE_MARKDOWN_LINK_{len(markdown_links) - 1}__"

    protected_text = re.sub(r"\[[^\]]+\]\(https?://[^)]+\)", protect_markdown_link, text)

    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^)\s]*)?'
    converted_text = re.sub(url_pattern, lambda m: f'[{m.group()}]({m.group()})', protected_text)

    for index, markdown_link in enumerate(markdown_links):
        converted_text = converted_text.replace(
            f"__GRUMMAGE_MARKDOWN_LINK_{index}__",
            markdown_link,
        )

    return converted_text

def is_running_in_snap():
    """Check if grummage is running inside a snap package."""
    return any(key.startswith("SNAP_") for key in os.environ)

def is_grype_installed():
    """Check if the grype binary is available in the system's PATH."""
    return shutil.which("grype") is not None

def get_grype_version():
    """Get the installed grype version."""
    try:
        result = subprocess.run(
            ["grype", "version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # Parse output like "Application: grype Version: 0.97.0"
            for line in result.stdout.splitlines():
                if "Version:" in line:
                    version = line.split("Version:")[1].strip()
                    # Remove 'v' prefix if present
                    return version.lstrip('v')
        return None
    except Exception:
        return None

def get_latest_grype_version():
    """Get the latest grype version from the upstream GitHub release."""
    try:
        req = urllib.request.Request(
            GRYPE_RELEASES_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": GRYPE_USER_AGENT,
            },
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            release = json.load(response)
            return release["tag_name"].lstrip("v")
    except Exception:
        return None


def get_latest_grype_release():
    """Get the latest grype release payload from GitHub."""
    req = urllib.request.Request(
        GRYPE_RELEASES_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": GRYPE_USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


def resolve_grype_release_asset(version, system_name=None, machine_name=None):
    """Resolve the release archive and binary name for the current platform."""
    system_name = system_name or platform.system()
    machine_name = (machine_name or platform.machine()).lower()

    arch_map = {
        ("linux", "x86_64"): ("linux", "amd64", "grype"),
        ("linux", "amd64"): ("linux", "amd64", "grype"),
        ("linux", "aarch64"): ("linux", "arm64", "grype"),
        ("linux", "arm64"): ("linux", "arm64", "grype"),
        ("darwin", "x86_64"): ("darwin", "amd64", "grype"),
        ("darwin", "amd64"): ("darwin", "amd64", "grype"),
        ("darwin", "arm64"): ("darwin", "arm64", "grype"),
    }

    target = arch_map.get((system_name.lower(), machine_name))
    if not target:
        raise RuntimeError(
            f"Automatic grype installation is not supported on {system_name}/{machine_name}."
        )

    platform_name, arch_name, binary_name = target
    archive_name = f"grype_{version}_{platform_name}_{arch_name}.tar.gz"
    checksum_name = f"grype_{version}_checksums.txt"
    return archive_name, checksum_name, binary_name


def download_file(url, destination):
    """Download a URL to a local file."""
    req = urllib.request.Request(url, headers={"User-Agent": GRYPE_USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response, open(destination, "wb") as output:
        output.write(response.read())


def read_expected_sha256(checksum_path, archive_name):
    """Read the expected sha256 for an archive from a checksum file."""
    with open(checksum_path, "r", encoding="utf-8") as checksum_file:
        for line in checksum_file:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[-1].endswith(archive_name):
                return parts[0]
    raise RuntimeError(f"Could not find checksum entry for {archive_name}.")


def sha256_file(path):
    """Calculate a file's sha256 digest."""
    digest = hashlib.sha256()
    with open(path, "rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_directory_to_path(directory):
    """Prepend a directory to PATH for the current process if it exists."""
    if not directory or not os.path.isdir(directory):
        return

    current_path = os.environ.get("PATH", "")
    path_parts = current_path.split(os.pathsep) if current_path else []
    if directory in path_parts:
        return

    os.environ["PATH"] = os.pathsep.join([directory, *path_parts]) if path_parts else directory


def open_debug_log(debug_log_path):
    """Open the optional debug log file, tolerating invalid paths."""
    if not debug_log_path:
        return None

    try:
        return open(debug_log_path, "a", encoding="utf-8")
    except OSError:
        return None

def compare_versions(current, latest):
    """Compare two version strings. Returns True if latest is newer than current."""
    try:
        # Split versions into parts and compare
        current_parts = [int(x) for x in current.split('.')]
        latest_parts = [int(x) for x in latest.split('.')]

        # Pad shorter version with zeros
        max_len = max(len(current_parts), len(latest_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        latest_parts.extend([0] * (max_len - len(latest_parts)))

        return latest_parts > current_parts
    except Exception:
        return False

def prompt_install_grype():
    """Prompt the user to install grype if it's not installed."""
    response = input(
        "The grype binary is not located in $PATH. Would you like to install it now? [y/N]: "
    ).strip().lower()
    return response == "y"

def install_grype():
    """Download and install the latest grype binary without invoking a shell pipeline."""
    try:
        release = get_latest_grype_release()
        version = release["tag_name"].lstrip("v")
        archive_name, checksum_name, binary_name = resolve_grype_release_asset(version)
        assets = {asset["name"]: asset["browser_download_url"] for asset in release.get("assets", [])}

        if archive_name not in assets or checksum_name not in assets:
            raise RuntimeError(f"Could not find release assets for grype v{version}.")

        install_dir = os.path.expanduser("~/.local/bin")
        os.makedirs(install_dir, exist_ok=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = os.path.join(temp_dir, archive_name)
            checksum_path = os.path.join(temp_dir, checksum_name)
            download_file(assets[archive_name], archive_path)
            download_file(assets[checksum_name], checksum_path)

            expected_sha256 = read_expected_sha256(checksum_path, archive_name)
            actual_sha256 = sha256_file(archive_path)
            if actual_sha256 != expected_sha256:
                raise RuntimeError("Downloaded grype archive failed checksum verification.")

            with tarfile.open(archive_path, "r:gz") as archive:
                member = next(
                    (item for item in archive.getmembers() if os.path.basename(item.name) == binary_name),
                    None,
                )
                if member is None:
                    raise RuntimeError(f"Archive did not contain {binary_name}.")
                member.name = binary_name
                archive.extract(member, temp_dir)

            extracted_binary = os.path.join(temp_dir, binary_name)
            destination_binary = os.path.join(install_dir, "grype")
            shutil.move(extracted_binary, destination_binary)
            os.chmod(destination_binary, 0o755)

        add_directory_to_path(install_dir)
        print(f"Grype v{version} successfully installed to {destination_binary}.")
        print("Added ~/.local/bin to PATH for this process.")
        print("Ensure ~/.local/bin is in your shell PATH before running grummage again.")
    except Exception as e:
        print(f"Failed to install grype: {e}")
        sys.exit(1)

class LoadingScreen(ModalScreen):
    """Modal screen showing loading progress."""

    DEFAULT_CSS = """
    LoadingScreen {
        align: center middle;
    }

    LoadingScreen > Vertical {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 2;
    }

    LoadingScreen > Vertical > Label {
        width: 100%;
        content-align: center middle;
        text-style: bold;
    }

    LoadingScreen > Vertical > #status {
        width: 100%;
        content-align: center middle;
        margin-top: 1;
    }

    LoadingScreen > Vertical > LoadingIndicator {
        width: 100%;
        height: 3;
        margin-top: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.status_label = Label("Initializing...", id="status")

    def compose(self):
        """Create child widgets for the loading screen."""
        with Vertical():
            yield Label("Grummage")
            yield self.status_label
            yield LoadingIndicator()

    def update_status(self, message):
        """Update the status message."""
        self.status_label.update(message)

class SearchModal(ModalScreen):
    """Modal screen for searching in the tree."""

    DEFAULT_CSS = """
    SearchModal {
        align: center middle;
    }

    SearchModal > Container {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }

    SearchModal > Container > Label {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }

    SearchModal > Container > Input {
        width: 100%;
    }
    """

    def compose(self):
        """Create child widgets for the search modal."""
        with Container():
            yield Label("Search")
            yield Input(placeholder="Enter search term...", id="search_input")

    def on_mount(self):
        """Focus the input when modal opens."""
        self.query_one("#search_input", Input).focus()

    def on_input_submitted(self, event):
        """Handle search submission."""
        search_term = event.value.strip()
        if search_term:
            self.dismiss(search_term)
        else:
            self.dismiss(None)

class Grummage(App):
    BINDINGS = [
        ("v", "load_tree_by_vulnerability", "by Vuln"),
        ("p", "load_tree_by_package_name", "by Pkg Name"),
        ("s", "load_tree_by_severity", "by Severity"),
        ("t", "load_tree_by_package_type", "by Type"),
        ("e", "explain_vulnerability", "Explain Vuln"),
        ("/", "search", "Search"),
        ("q", "quit", "Quit"),
        ("j", "simulate_key('down')", "Move down"),
        ("k", "simulate_key('up')", "Move up"),
        ("h", "simulate_key('left')", "Move left"),
        ("l", "simulate_key('right')", "Move right"),
    ]

    def __init__(self, sbom_file=None):
        super().__init__()
        self.sbom_file = sbom_file
        self.vulnerability_report = None
        self.debug_log_file = open_debug_log(os.environ.get("GRUMMAGE_DEBUG_LOG"))
        self.selected_vuln_id = None
        self.selected_package_name = None
        self.selected_package_version = None
        self.detailed_text = None
        self.view_mode = "by_package"  # Track current view mode
        self.search_term = None  # Current search term
        self.search_results = []  # List of matching nodes
        self.search_index = -1  # Current position in search results

    def quit(self):
        """Exit the application."""
        self.exit()

    def debug_log(self, message):
        """Helper method to write debug messages to log file."""
        if self.debug_log_file is not None:
            self.debug_log_file.write(message + "\n")
            self.debug_log_file.flush()

    async def on_mount(self):
        self.debug_log("on_mount: Starting application setup")

        # Initialize widgets for the tree view, details display, and status bar
        self.tree_view = Tree("Packages")  # Default to "Packages" since default view is by_package
        self.details_display = Markdown("Select a node for more details.")
        self.status_bar = Static("Status: Initializing...")

        # Create containers for tree view (left) and details (right) in a horizontal layout
        tree_container = Container(self.tree_view)
        details_container = VerticalScroll(self.details_display)
        # Set widths to maintain a 30/70 side-by-side layout
        tree_container.styles.width = "35%"
        details_container.styles.width = "65%"
        tree_container.styles.height = "98%"
        details_container.styles.height = "98%"

        # Use Horizontal container for side-by-side layout
        main_layout = Horizontal(tree_container, details_container)
        main_layout.styles.height = "98%"

        # Mount the main layout and the status bar at the bottom
        await self.mount(main_layout)
        await self.mount(self.status_bar)
        await self.mount(Footer())
        self.debug_log("on_mount: Layout mounted")

        # Show loading screen and load the SBOM from file or stdin
        self.loading_screen = LoadingScreen()
        await self.push_screen(self.loading_screen)
        await self.load_sbom()

    def check_grype_db(self):
        """Check if grype vulnerability database needs updating."""
        try:
            result = subprocess.run(
                ["grype", "db", "check", "-o", "json"],
                capture_output=True,
                text=True
            )

            db_status = json.loads(result.stdout)
            return db_status.get("updateAvailable", False)
        except Exception as e:
            self.debug_log(f"Error checking grype database: {e}")
            return False

    def update_grype_db(self):
        """Update the grype vulnerability database (blocking)."""
        try:
            self.debug_log("Starting grype database update")
            result = subprocess.run(
                ["grype", "db", "update"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.notify("Vulnerability database updated successfully", severity="information")
                self.debug_log("Grype database updated successfully")
                return True
            else:
                self.notify(f"Database update failed: {result.stderr}", severity="error")
                self.debug_log(f"Grype database update failed: {result.stderr}")
                return False
        except Exception as e:
            self.notify(f"Database update error: {e}", severity="error")
            self.debug_log(f"Exception during database update: {e}")
            return False

    def update_loading_status(self, message):
        """Update both loading screen and status bar."""
        if hasattr(self, 'loading_screen') and self.loading_screen:
            self.loading_screen.update_status(message)
        self.status_bar.update(f"Status: {message}")

    @work(thread=True, exclusive=True)
    def load_sbom_worker(self):
        """Load SBOM and run grype analysis in worker thread."""
        # Check grype binary version (skip if running in snap)
        if not is_running_in_snap():
            self.app.call_from_thread(self.update_loading_status, "Checking grype version...")
            self.debug_log("Checking grype binary version")

            current_version = get_grype_version()
            latest_version = get_latest_grype_version()

            if current_version and latest_version:
                self.debug_log(f"Grype version: current={current_version}, latest={latest_version}")
                if compare_versions(current_version, latest_version):
                    self.app.call_from_thread(
                        self.notify,
                        f"Grype update available: v{latest_version} (installed: v{current_version})",
                        severity="warning"
                    )
                    self.debug_log(f"Grype update available: {current_version} -> {latest_version}")
            else:
                self.debug_log("Could not check grype version")
        else:
            self.debug_log("Running in snap, skipping grype version check")

        # Check and update grype database if needed
        self.app.call_from_thread(self.update_loading_status, "Checking vulnerability database...")
        self.debug_log("Checking grype database status")

        if self.check_grype_db():
            self.app.call_from_thread(self.update_loading_status, "Updating vulnerability database - this may take a minute...")
            self.debug_log("Database update available, starting update")
            if not self.update_grype_db():
                # Update failed, abort
                self.app.call_from_thread(self.update_loading_status, "Database update failed")
                self.app.call_from_thread(self.notify, "Database update failed", severity="error")
                self.app.call_from_thread(self.pop_screen)
                return
        else:
            self.debug_log("Database is up to date")

        # Load SBOM
        self.app.call_from_thread(self.update_loading_status, "Loading SBOM file...")
        if self.sbom_file:
            # Load SBOM from the provided file path
            self.debug_log(f"Loading SBOM from file: {self.sbom_file}")
            sbom_json = self.load_json(self.sbom_file)
        else:
            # Read SBOM from stdin
            self.debug_log("Loading SBOM from stdin")
            try:
                sbom_json = json.load(sys.stdin)
            except json.JSONDecodeError as e:
                self.debug_log(f"Error reading SBOM from stdin: {e}")
                self.app.call_from_thread(self.update_loading_status, "Failed to read SBOM from stdin")
                self.app.call_from_thread(self.notify, "Failed to read SBOM from stdin", severity="error")
                self.app.call_from_thread(self.pop_screen)
                return

        if not sbom_json:
            self.app.call_from_thread(self.update_loading_status, "Failed to load SBOM")
            self.app.call_from_thread(self.notify, "Failed to load SBOM", severity="error")
            self.app.call_from_thread(self.pop_screen)
            return

        # Now run grype analysis (still in same worker thread)
        self.run_grype_analysis(sbom_json)

    def run_grype_analysis(self, sbom_json):
        """Run grype analysis on SBOM (called from worker thread)."""
        temp_file_path = None
        try:
            self.app.call_from_thread(self.update_loading_status, "Analyzing SBOM with grype...")
            self.debug_log("Starting grype analysis")

            # Create a temporary file to store the SBOM JSON
            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json') as temp_file:
                json.dump(sbom_json, temp_file)
                temp_file_path = temp_file.name

            # Call Grype using the temporary JSON file path
            result = subprocess.run(
                ["grype", temp_file_path, "-o", "json"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.debug_log(f"Grype encountered an error: {result.stderr}")
                self.app.call_from_thread(self.update_loading_status, "Grype analysis failed")
                self.app.call_from_thread(self.notify, f"Grype analysis failed: {result.stderr}", severity="error")
                self.app.call_from_thread(self.pop_screen)
                return

            # Parse the JSON result
            vulnerability_report = json.loads(result.stdout)

            # Update UI from thread
            self.app.call_from_thread(self.on_grype_complete, vulnerability_report)

        except Exception as e:
            self.debug_log(f"Error running Grype: {e}")
            self.app.call_from_thread(self.update_loading_status, "Error running grype")
            self.app.call_from_thread(self.notify, f"Error running grype: {e}", severity="error")
            self.app.call_from_thread(self.pop_screen)
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    async def load_sbom(self):
        """Initiate SBOM loading and analysis."""
        self.load_sbom_worker()

    def load_json(self, file_path):
        """Load SBOM JSON from a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            self.debug_log(f"Error loading SBOM JSON: {e}")
            return None

    def on_grype_complete(self, vulnerability_report):
        """Handle completion of grype analysis (called from worker thread)."""
        self.vulnerability_report = vulnerability_report

        if self.vulnerability_report and "matches" in self.vulnerability_report:
            num_vulns = len(self.vulnerability_report["matches"])
            self.load_tree_by_package_name()
            self.status_bar.update("Status: Vulnerability data loaded. Press N, T, V, S to change views, or E to explain.")
            self.notify(f"Analysis complete - found {num_vulns} vulnerabilities", severity="information")
            self.debug_log(f"Vulnerability data loaded into tree: {num_vulns} matches")
        else:
            self.status_bar.update("Status: No vulnerabilities found.")
            self.notify("No vulnerabilities found", severity="information")
            self.debug_log("No vulnerability data found")

        # Dismiss the loading screen now that we're done
        self.pop_screen()
    
    def load_tree_by_package_name(self):
        """Display vulnerabilities organized by package name."""
        self.view_mode = "by_package"
        self.search_results = []  # Clear search when changing views
        self.search_index = -1
        self.tree_view.clear()
        self.tree_view.root.label = "Packages"
        file_name_map = {}
        for match in self.vulnerability_report["matches"]:
            file_name = match["artifact"]["name"]
            file_name_map.setdefault(file_name, []).append(match)

        for file_name, matches in file_name_map.items():
            file_node = self.tree_view.root.add(file_name)
            for match in matches:
                vuln_id = match["vulnerability"]["id"]
                vuln_node = file_node.add_leaf(f"{vuln_id}")

                # Store detailed info for right-hand pane display
                vuln_node.data = {
                    "id": vuln_id,
                    "package_name": match["artifact"]["name"],
                    "package_version": match["artifact"]["version"],
                    "severity": match["vulnerability"].get("severity", "Unknown"),
                    "fix_version": match["vulnerability"].get("fix", {}).get("versions", ["None"]),
                    "related": match.get("relatedVulnerabilities", [])
                }

        # Expand root to show the tree
        self.tree_view.root.expand()

    def load_tree_by_type(self):
        """Display vulnerabilities organized by package type, with package names under each type."""
        self.view_mode = "by_type"
        self.search_results = []  # Clear search when changing views
        self.search_index = -1
        self.tree_view.clear()
        self.tree_view.root.label = "Package Types"
        type_map = {}

        # Organize matches by package type and then by package name
        for match in self.vulnerability_report["matches"]:
            pkg_type = match["artifact"]["type"]
            pkg_name = match["artifact"]["name"]
            type_map.setdefault(pkg_type, {}).setdefault(pkg_name, []).append(match)

        # Build the tree view with the new structure
        for pkg_type, packages in type_map.items():
            type_node = self.tree_view.root.add(pkg_type)  # Add package type node
            for pkg_name, matches in packages.items():
                package_node = type_node.add(pkg_name)  # Add package name node
                for match in matches:
                    vuln_id = match["vulnerability"]["id"]
                    vuln_node = package_node.add_leaf(f"{vuln_id}")  # Add vulnerability ID under package name

                    # Store detailed info for right-hand pane display
                    vuln_node.data = {
                        "id": vuln_id,
                        "package_name": match["artifact"]["name"],
                        "package_version": match["artifact"]["version"],
                        "severity": match["vulnerability"].get("severity", "Unknown"),
                        "fix_version": match["vulnerability"].get("fix", {}).get("versions", ["None"]),
                        "related": match.get("relatedVulnerabilities", [])
                    }

        # Expand root to show the tree
        self.tree_view.root.expand()


    def load_tree_by_vulnerability(self):
        """Display vulnerabilities organized by vulnerability ID."""
        self.view_mode = "by_vuln"
        self.search_results = []  # Clear search when changing views
        self.search_index = -1
        self.tree_view.clear()
        self.tree_view.root.label = "Vulnerabilities"
        vuln_map = {}
        for match in self.vulnerability_report["matches"]:
            vuln_id = match["vulnerability"]["id"]
            vuln_map.setdefault(vuln_id, []).append(match)

        for vuln_id, matches in vuln_map.items():
            vuln_node = self.tree_view.root.add(vuln_id)
            for match in matches:
                pkg_name = match["artifact"]["name"]
                package_node = vuln_node.add_leaf(f"{pkg_name}")

                # Store detailed info for right-hand pane display
                package_node.data = {
                    "id": vuln_id,
                    "package_name": match["artifact"]["name"],
                    "package_version": match["artifact"]["version"],
                    "severity": match["vulnerability"].get("severity", "Unknown"),
                    "fix_version": match["vulnerability"].get("fix", {}).get("versions", ["None"]),
                    "related": match.get("relatedVulnerabilities", [])
                }

        # Expand root to show the tree
        self.tree_view.root.expand()

    def load_tree_by_severity(self):
        """Display vulnerabilities organized by severity, in fixed order."""
        self.view_mode = "by_severity"
        self.search_results = []  # Clear search when changing views
        self.search_index = -1
        self.tree_view.clear()
        self.tree_view.root.label = "Severity Levels"
        # Define the desired order for severities
        severity_order = ["Critical", "High", "Medium", "Low", "Negligible", "Unknown"]

        # Create a dictionary mapping each severity to its matches
        severity_map = {severity: [] for severity in severity_order}
        for match in self.vulnerability_report["matches"]:
            severity = match["vulnerability"].get("severity", "Unknown")
            if severity not in severity_map:
                severity = "Unknown"  # Assign unknown severity if it's not one of the predefined categories
            severity_map[severity].append(match)

        # Add nodes in the specified order with full vulnerability data for each node
        for severity in severity_order:
            if severity_map[severity]:  # Only add if there are matches
                severity_node = self.tree_view.root.add(severity)
                for match in severity_map[severity]:
                    vuln_id = match["vulnerability"]["id"]
                    package_name = match["artifact"]["name"]
                    vuln_node = severity_node.add_leaf(f"{vuln_id} ({package_name})")

                    # Store detailed info in each node for later access in the right-hand pane
                    vuln_node.data = {
                        "id": vuln_id,
                        "package_name": match["artifact"]["name"],
                        "package_version": match["artifact"]["version"],
                        "severity": severity,
                        "fix_version": match["vulnerability"].get("fix", {}).get("versions", ["None"]),
                        "related": match.get("relatedVulnerabilities", [])
                    }

        # Expand root to show the tree
        self.tree_view.root.expand()



    async def on_key(self, event):
        """Handle dedicated search-navigation keys not covered by BINDINGS."""
        key = event.key

        # Handle search navigation (n and N are dedicated to search)
        if key == "n":
            # Find next search result
            if self.search_results:
                self.find_next()
            else:
                self.notify("No active search. Press '/' to search.", severity="information")
            return
        elif key == "N":
            # Find previous search result (Shift+N)
            if self.search_results:
                self.find_previous()
            else:
                self.notify("No active search. Press '/' to search.", severity="information")
            return


    async def on_tree_node_selected(self, event):
        """Show detailed information for the selected vulnerability."""
        node = event.node
        if node.data:
            details = node.data
            self.selected_vuln_id = details["id"]
            self.selected_package_name = details["package_name"]
            self.selected_package_version = details["package_version"]
            self.status_bar.update(f"Status: Selected {details['id']} in {details['package_name']} ({details['package_version']})")
            detail_text = (
                f"# {details['id']}\n\n"
                f"**Package:** {details['package_name']} ({details['package_version']})\n\n"
                f"**Severity:** {details['severity']}\n\n"
                f"**Fix Version:** {', '.join(details['fix_version'])}\n\n"
                f"**Related Vulnerabilities:**\n\n"
            )
            for related in details["related"]:
                detail_text += f"* {related['id']} ({related['dataSource']})\n"
            
            # Convert URLs to markdown links
            detail_text = format_urls_as_markdown(detail_text)
            
            self.debug_log(f"Displaying details for {details['id']}")
            self.details_display.update(detail_text)
            self.detailed_text = detail_text
        else:
            self.details_display.update("No data found for selected node.")
            self.selected_vuln_id = None
            self.selected_package_name = None
            self.selected_package_version = None
            self.debug_log("No data found for selected node.")

    async def action_search(self):
        """Open search modal and perform search."""
        async def handle_search_result(search_term):
            if search_term:
                await self.perform_search(search_term)

        await self.push_screen(SearchModal(), callback=handle_search_result)

    async def perform_search(self, search_term):
        """Search for nodes matching the search term in the current tree."""
        self.search_term = search_term
        self.search_results = []
        self.search_index = -1

        # Search through all nodes in the tree
        def search_nodes(node):
            """Recursively search through tree nodes."""
            # Get the label text
            label_text = str(node.label).lower()
            search_lower = search_term.lower()

            # Check if this node matches
            if search_lower in label_text and node != self.tree_view.root:
                self.search_results.append(node)

            # Search children
            for child in node.children:
                search_nodes(child)

        # Start search from root
        search_nodes(self.tree_view.root)

        if self.search_results:
            self.search_index = 0
            # Use call_after_refresh to ensure the tree is ready
            self.call_after_refresh(self.select_search_result)
            self.status_bar.update(f"Status: Found {len(self.search_results)} results for '{search_term}'. Press 'n' for next, 'N' for previous.")
            self.notify(f"Found {len(self.search_results)} results", severity="information")
            self.debug_log(f"Search for '{search_term}' found {len(self.search_results)} results")
        else:
            self.status_bar.update(f"Status: No results found for '{search_term}'")
            self.notify(f"No results found for '{search_term}'", severity="warning")
            self.debug_log(f"Search for '{search_term}' found no results")

    def find_next(self):
        """Navigate to the next search result."""
        if not self.search_results:
            return

        self.search_index = (self.search_index + 1) % len(self.search_results)
        self.select_search_result()

    def find_previous(self):
        """Navigate to the previous search result."""
        if not self.search_results:
            return

        self.search_index = (self.search_index - 1) % len(self.search_results)
        self.select_search_result()

    def select_search_result(self):
        """Select and focus on the current search result."""
        if not self.search_results or self.search_index < 0:
            return

        node = self.search_results[self.search_index]

        # Expand parent nodes to make this node visible
        current = node.parent
        while current and current != self.tree_view.root:
            current.expand()
            current = current.parent

        # Select the node
        self.tree_view.select_node(node)
        node.expand()

        # Update status
        self.status_bar.update(
            f"Status: Result {self.search_index + 1}/{len(self.search_results)} for '{self.search_term}' - "
            f"Press 'n' for next, 'N' for previous"
        )
        self.debug_log(f"Navigated to search result {self.search_index + 1}/{len(self.search_results)}")

    def on_unmount(self):
        """Close the log file when the application exits."""
        if self.debug_log_file is not None:
            self.debug_log_file.close()

    @work(thread=True, exclusive=True)
    def explain_vulnerability_worker(self, vuln_id, detailed_text):
        """Call Grype to explain a vulnerability by its ID (worker thread)."""
        try:
            self.app.call_from_thread(self.notify, f"Requesting explanation for {vuln_id}...", severity="information")
            self.debug_log(f"Starting grype explain for {vuln_id}")

            if not self.vulnerability_report:
                self.app.call_from_thread(self.details_display.update, "# Error\n\nNo vulnerability report is loaded.")
                self.app.call_from_thread(self.notify, "No vulnerability report is loaded", severity="error")
                return

            # Run Grype's explain command with the specific vulnerability ID
            explain_result = subprocess.run(
                ["grype", "explain", "--id", vuln_id],
                input=json.dumps(self.vulnerability_report),
                capture_output=True,
                text=True
            )

            # Check and display the result in the details pane
            if explain_result.returncode == 0:
                explanation = explain_result.stdout
                combined_text = (
                    f"{detailed_text}\n\n\n"  # Add two blank lines for spacing
                    f"## Explanation for {vuln_id}:\n\n"
                    f"{explanation}"
                )
                combined_text = format_urls_as_markdown(combined_text)
                self.app.call_from_thread(self.details_display.update, combined_text)
                self.app.call_from_thread(self.notify, f"Explanation for {vuln_id} loaded", severity="information")
                self.debug_log(f"Displaying explanation for {vuln_id}")
            else:
                error_text = f"# Error\n\nFailed to explain {vuln_id}.\n\nError: {explain_result.stderr}"
                self.app.call_from_thread(self.details_display.update, error_text)
                self.app.call_from_thread(self.notify, f"Failed to explain {vuln_id}", severity="error")
                self.debug_log(f"Error explaining {vuln_id}: {explain_result.stderr}")

        except Exception as e:
            error_text = f"# Error\n\nError explaining {vuln_id}: {e}"
            self.app.call_from_thread(self.details_display.update, error_text)
            self.app.call_from_thread(self.notify, f"Error explaining {vuln_id}", severity="error")
            self.debug_log(f"Exception in explain_vulnerability: {e}")


def main():
    """Main entry point for the grummage CLI."""
    parser = argparse.ArgumentParser(
        prog="grummage",
        description="Interactive terminal frontend for Grype to view vulnerabilities",
        epilog="Example: grummage my-app.spdx.json",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "sbom_file",
        help="Path to the SBOM file to analyze"
    )

    # Add custom help text for navigation with updated keybindings
    parser.epilog = """Navigation:
  • Arrow keys or h/j/k/l - Navigate
  • Enter - Select item

Views:
  • p - View by Package name
  • v - View by Vulnerability
  • t - View by Type
  • s - View by Severity

Search:
  • / - Search within current view
  • n - Find next result
  • N - Find previous result

Actions:
  • e - Explain vulnerability (when available)
  • q - Quit

Example:
  grummage my-app.spdx.json"""

    args = parser.parse_args()
    sbom_file = args.sbom_file
    if not is_grype_installed():
        if prompt_install_grype():
            install_grype()
        else:
            print(
                "The grype binary is not located in $PATH and the option to install was deferred."
            )
            sys.exit(0)

    Grummage(args.sbom_file).run()

if __name__ == "__main__":
    main()
