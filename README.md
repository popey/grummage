# Grummage

Grype + Rummage = Grummage.

Grummage is an interactive terminal frontend to [Grype](https://github.com/anchore/grype).

![A short video showing Grummage](./grummage.gif)

## Introduction

[Grype](https://github.com/anchore/grype) is an awesome vulnerability scanner. It produces minimal textual output, or verbose JSON files. I wanted something to rummage around in the json, without having to learn arcane jq syntax ;).

So Grummage was born.

## Installation

Grummage is written in Python, and uses the Textual library for the UI.

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

### Get Grummage

I use [uv](https://github.com/astral-sh/uv) to manage Python virtual environments. It's good. You might like it too.

```shell
git clone https://github.com/popey/grummage
cd grummage
uv venv
source ./venv/bin/activate
uv pip install textual
```

## Usage

Point grummage at an SBOM (Software Bill of Materials). 

```shell
./grummage ./example_sboms/nextcloud-latest-syft-sbom.json
```

Grummage will load the SBOM and pass it through Grype to build the vulnerability list. 
Use the cursor keys or mouse to navigate the tree on the left pane.
Press Enter or mouse click on a vulnerability to obtain limited details.

### Keys:

* `e` - Request further details via `grype explain`
* `q` - Quit

Sort by:

* `n` - Name of package
* `v` - Vulnerability ID
* `t` - Type of package
* `s` - Severity of issue

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

## Caveats

I am not a developer. This is all rather hastily written. No warranty is provided or implied.