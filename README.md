# Grummage

Grype + Rummage = Grummage.

Grummage is an interactive terminal frontend to [Grype](https://github.com/anchore/grype).

![A short video showing Grummage](./grummage.gif)

## Introduction

[Grype](https://github.com/anchore/grype) is an awesome vulnerability scanner. It produces minimal textual output, or verbose JSON files. I wanted something to rummage around in the json, without having to learn arcane jq syntax ;).

So Grummage was born.

## Installation

Grummage is written in Python and requires Python 3.8 or later.

### Pre-requisites

Grummage requires the [Grype](https://github.com/anchore/grype) binary in your path to function.

You may want to confirm the Grype command line works, and has updated the vulnerability database first.

```shell
grype --version
```

```
grype 0.84.0
```

```shell
grype db update
```

```
  ✔ Vulnerability DB                [no update available]
 No vulnerability database update available
```

### From PyPI (Recommended)

The easiest way to install grummage is from PyPI:

```shell
pip install grummage
```

### From GitHub Releases

Download the latest release from the [GitHub releases page](https://github.com/popey/grummage/releases).

### Using Homebrew (macOS/Linux)

```shell
brew tap popey/grummage
brew install grummage
```

### Using Docker

Note: `-it` is required for interaction with the application. Setting the `TERM` variable allows for better colour support.

```shell
docker run --rm -it -e TERM=xterm-256color -v $(pwd):/data ghcr.io/popey/grummage:latest /data/your-sbom.json
```

### Using Snap

```shell
sudo snap install grummage
```

### From Source

For development or if you prefer to install from source:

```shell
git clone https://github.com/popey/grummage
cd grummage
pip install -e .
```

### Using uv (Alternative)

If you use [uv](https://github.com/astral-sh/uv) for Python environment management:

```shell
git clone https://github.com/popey/grummage
cd grummage
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

## Usage

Point grummage at an SBOM (Software Bill of Materials):

```shell
grummage ./example_sboms/nextcloud-latest-syft-sbom.json
```

Grummage will check the grype vulnerability database, update it if needed, then load the SBOM and analyze it with Grype. A loading screen shows progress during these operations.

Once loaded, use the cursor keys or mouse to navigate the tree on the left pane.
Press Enter or mouse click on a vulnerability to obtain limited details.

### Keys:

**Navigation:**
* Arrow keys or `h`/`j`/`k`/`l` - Navigate the tree
* Enter - Select item

**Views:**
* `p` - View by package name
* `v` - View by vulnerability ID
* `t` - View by package type
* `s` - View by severity

**Search:**
* `/` - Search within current view
* `n` - Find next result
* `N` - Find previous result

**Actions:**
* `e` - Request further details via `grype explain`
* `q` - Quit

## Making SBOMs

I use [Syft](https://github.com/anchore/syft) to generate SBOMs, but other tools are available. For example:

```shell
syft nextcloud:latest -o syft-json=nextcloud-latest-syft-sbom.json
```

```
 ✔ Loaded image       nextcloud:latest
 ✔ Parsed image       sha256:44c884988b43e01e1434a66f58943dc809a193abf1a6df0f2cebad450e587ad7
 ✔ Cataloged contents bdca3ed5b303726bba5579564ab8fe5df700d637ae04f00689443260b26cc832
   ├── ✔ Packages                        [418 packages]
   ├── ✔ File digests                    [10,605 files]
   ├── ✔ File metadata                   [10,605 locations]
   └── ✔ Executables                     [1,317 executables]
```

## Distribution

Grummage is available through multiple distribution channels:

- **PyPI**: `pip install grummage`
- **Homebrew**: `brew tap popey/grummage && brew install grummage`
- **Docker**: `ghcr.io/popey/grummage:latest`
- **Snap**: `sudo snap install grummage`
- **GitHub Releases**: Pre-built packages available

## Caveats

I am an open-source enthusiast and self-taught coder creating projects driven by curiosity and a love for problem-solving. The code may have bugs or sharp edges. Kindly let me know if you find one, via an [issue](https://github.com/popey/grummage/issues). Thanks.
