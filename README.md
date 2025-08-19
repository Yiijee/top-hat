# top-hat

[![License MIT](https://img.shields.io/pypi/l/top-hat.svg?color=green)](https://github.com/Yiijee/top-hat/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/top-hat.svg?color=green)](https://pypi.org/project/top-hat)
[![Python Version](https://img.shields.io/pypi/pyversions/top-hat.svg?color=green)](https://python.org)
[![tests](https://github.com/Yiijee/top-hat/workflows/tests/badge.svg)](https://github.com/Yiijee/top-hat/actions)
[![codecov](https://codecov.io/gh/Yiijee/top-hat/branch/main/graph/badge.svg)](https://codecov.io/gh/Yiijee/top-hat)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/top-hat)](https://napari-hub.org/plugins/top-hat)
[![npe2](https://img.shields.io/badge/plugin-npe2-blue?link=https://napari.org/stable/plugins/index.html)](https://napari.org/stable/plugins/index.html)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-purple.json)](https://github.com/copier-org/copier)

Mapping hemilineage associate tracts in light microscopy images.

This tool is still under developing and only avaible for Clowney lab internal use.

To-do:
- [ ] Complete documentation
- [ ] Release the first version

----------------------------------

This [napari] plugin was generated with [copier] using the [napari-plugin-template].

<!--
Don't miss the full getting started guide to set up your new package:
https://github.com/napari/napari-plugin-template#getting-started

and review the napari docs for plugin developers:
https://napari.org/stable/plugins/index.html
-->



## Installation

Currently top-hat support python 3.10~3.12. Other versions might work but haven't beed tested.
Using this package in a virtual enviroment is recommened.
Install [miniconda](https://www.anaconda.com/docs/getting-started/miniconda/main) following their instruction.


To create an enviroment and enter it:
```bash
conda create -n <env_name> python==3.12
conda activate <env_name>
```
*you can replace `<env_name>` with any name you prefer.*

To install latest development version :
```
pip install "git+https://github.com/Yiijee/top-hat.git#egg=top-hat[all]"
```

To clone this repo and make edits:
```
git clone https://github.com/Yiijee/top-hat.git
cd top-hat
git install -e ".[all]"
```

## Get started

Open a terminal, run following codes to start a GUI. Note that `<env_name>` should be your own enviroment name.

```
conda activate <env_name>
napari
```
A napari user interface will appear. You can use plugin>Top HAT to select one of the modules from `hat viewer` or `top match`.
You can drag-drop a **single channel, registered** nrrd or tif image into the user iterface to open it.

### Top match

Run a cellbody-tract matching with human in the loop. Documents to be updated.

### Hat viewer

Search and select existing hemilineage tracts, cellbody fiber or whole neurons, co-visualize with your registered image. You can save the tracts with JRC2018U template into an png or pdf file. Documents to be updated.



## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [MIT] license,
"top-hat" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[napari]: https://github.com/napari/napari
[copier]: https://copier.readthedocs.io/en/stable/
[@napari]: https://github.com/napari
[MIT]: http://opensource.org/licenses/MIT
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[GNU GPL v3.0]: http://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: http://www.gnu.org/licenses/lgpl-3.0.txt
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[napari-plugin-template]: https://github.com/napari/napari-plugin-template

[file an issue]: https://github.com/Yiijee/top-hat/issues

[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
