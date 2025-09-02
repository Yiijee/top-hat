"""
This module is an example of a barebones writer plugin for napari.

It implements the Writer specification.
see: https://napari.org/stable/plugins/building_a_plugin/guides.html#writers

Replace code below according to your needs.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    DataType = Union[Any, Sequence[Any]]
    FullLayerData = tuple[DataType, dict, str]


def write_single_image(path: str, data: Any, meta: dict) -> list[str]:
    """Writes a single image layer to a file.

    Args:
        path (str): A string path indicating where to save the image file.
        data (Any): The layer data, corresponding to the `.data` attribute
            from a napari layer.
        meta (dict): A dictionary containing all other attributes from the
            napari layer (excluding the `.data` attribute).

    Returns:
        list[str]: A list containing the string path to the saved file.
    """

    # implement your writer logic here ...

    # return path to any file(s) that were successfully written
    return [path]


def write_multiple(path: str, data: list[FullLayerData]) -> list[str]:
    """Writes multiple layers of different types to a file.

    Args:
        path (str): A string path indicating where to save the data file(s).
        data (list[FullLayerData]): A list of layer tuples. Each tuple
            contains three elements: (data, meta, layer_type).
            - `data`: The layer data.
            - `meta`: A dictionary containing all other metadata attributes
              from the napari layer (excluding the `.data` attribute).
            - `layer_type`: A string indicating the layer type (e.g.,
              "image", "labels", "surface").

    Returns:
        list[str]: A list containing paths to the saved file(s).
    """

    # implement your writer logic here ...

    # return path to any file(s) that were successfully written
    return [path]
