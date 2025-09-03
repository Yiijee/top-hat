# Hi-HAT

[![License MIT](https://img.shields.io/pypi/l/hi-hat.svg?color=green)](https://github.com/Yiijee/hi-hat/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/hi-hat.svg?color=green)](https://pypi.org/project/hi-hat)
[![Python Version](https://img.shields.io/pypi/pyversions/hi-hat.svg?color=green)](https://python.org)
[![tests](https://github.com/Yiijee/hi-hat/workflows/tests/badge.svg)](https://github.com/Yiijee/hi-hat/actions)
[![codecov](https://codecov.io/gh/Yiijee/hi-hat/branch/main/graph/badge.svg)](https://codecov.io/gh/Yiijee/hi-hat)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/hi-hat)](https://napari-hub.org/plugins/hi-hat)
[![npe2](https://img.shields.io/badge/plugin-npe2-blue?link=https://napari.org/stable/plugins/index.html)](https://napari.org/stable/plugins/index.html)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-purple.json)](https://github.com/copier-org/copier)

Mapping hemilineage-associated tracts in light microscopy images.

This tool is still under development and is currently only available for Clowney Lab internal use.

----------------------------------

This [napari](https://github.com/napari/napari) plugin was generated with [copier](https://copier.readthedocs.io/en/stable/) using the [napari-plugin-template](https://github.com/napari/napari-plugin-template).

<!--
Don't miss the full getting started guide to set up your new package:
https://github.com/napari/napari-plugin-template#getting-started

and review the napari docs for plugin developers:
https://napari.org/stable/plugins/index.html
-->

## Most recent updates

Rename the project from top-HAT to Hi-HAT.

Rename top match to Hi Match.

Need to install this package again using pip.



## Installation

Currently, Hi-HAT supports Python 3.10-3.12. Other versions might work but have not been tested.
Using this package in a virtual environment is recommended.
Install [miniconda](https://www.anaconda.com/docs/getting-started/miniconda/main) following their instructions.


To create an environment and enter it:
```bash
conda create -n <env_name> python==3.12
conda activate <env_name>
```
*you can replace `<env_name>` with any name you prefer.*

To install latest development version :
```
pip install "git+https://github.com/Yiijee/hi-hat.git#egg=hi-hat[all]"
```

To clone this repo and make edits:
```
git clone https://github.com/Yiijee/hi-hat.git
cd hi-hat
pip install -e ".[all]"
```

## Get started

Open a terminal and run the following commands to start the GUI. Note that `<env_name>` should be your own environment name.

```
conda activate <env_name>
napari
```
The napari user interface will appear. You can then navigate to **Plugins > Hi-HAT** to select either the `HAT viewer` or `Hi Match` module.

You can drag and drop a **single-channel, registered** .nrrd or .tif image into the user interface to open it.

>Check [this document](https://github.com/Yiijee/flybrain_registration/blob/main/GL_cmtk_code/GL_warp_batch_JRC2018U_usage.md) about registration codes.

### Hi Match

Run a cell-body-tract matching process with a human-in-the-loop. Check [Hi Match tutorial](hi_match.md) for details.

<img src="figures/top_match_overview.png" alt="Top Match initial interface" width="100%">

### HAT Viewer

Search for and select existing hemilineage tracts, cell body fibers, or whole neurons, and co-visualize them with your registered image. You can save the tracts with the JRC2018U template into a .png or .pdf file. Check [HAT viewer tutorial](hat_viewer.md) for details.

<img src="figures/hat_viewer_initial.png" alt="HAT Viewer initial interface" width="100%">



## Contributing
