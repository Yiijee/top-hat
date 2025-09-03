# load hemilineage data from a target directory

import pickle
from pathlib import Path
from typing import Any

import nrrd
import numpy as np
import numpy.typing as npt
import pandas as pd


class FAFB_loader:
    """Handles loading FAFB hemilineage data from a directory.

    This class validates the integrity of the dataset and provides methods
    to access different data components, such as neuron skeletons, voxel masks,
    and NBLAST dotprops.

    Attributes:
        fafb_root (Path): The root directory of the FAFB dataset.
        hemilineage_list (list[str]): A list of hemilineage names.
        hemilineage_df (pd.DataFrame): A DataFrame containing summary
            information about the hemilineages.
    """

    def __init__(self, path: str, hemilineage_number: int = 197):
        """Initializes the loader and validates the data path.

        Args:
            path (str): The root path of the FAFB dataset.
            hemilineage_number (int): The expected number of hemilineages.
        """
        self.fafb_root = Path(path)
        self.hemilineage_list: list[str] = []
        self._read_hemilineage_list(hemilineage_number)
        self.hemilineage_df: pd.DataFrame = pd.DataFrame()

    def _read_hemilineage_list(self, hemilineage_number: int):
        """Reads the hemilineage list from the summary CSV.

        Args:
            hemilineage_number (int): The expected number of hemilineages.

        Raises:
            FileNotFoundError: If the root path or summary CSV does not exist.
            NotADirectoryError: If the root path is not a directory.
            ValueError: If the number of found hemilineages does not match
                the expected number.
        """
        if not self.fafb_root.exists():
            raise FileNotFoundError(f"Path {self.fafb_root} does not exist.")
        if not self.fafb_root.is_dir():
            raise NotADirectoryError(
                f"Path {self.fafb_root} is not a directory."
            )

        hemilineage_csv = self.fafb_root / "hemilineage_summary.csv"
        if not hemilineage_csv.exists():
            raise FileNotFoundError(
                f"Dataset is not complete, missing {hemilineage_csv}"
            )

        self.hemilineage_df = pd.read_csv(hemilineage_csv)
        self.hemilineage_list = self.hemilineage_df[
            "ito_lee_hemilineage"
        ].tolist()

        if len(self.hemilineage_list) != hemilineage_number:
            raise ValueError(
                f"Expected {hemilineage_number} hemilineages, "
                f"but found {len(self.hemilineage_list)}."
            )

    def get_somas(self) -> pd.DataFrame:
        """Gets the somas data for all hemilineages.

        Returns:
            pd.DataFrame: A DataFrame containing soma information.
        """
        hemilineage_csv = self.fafb_root / "hemilineage_summary.csv"
        self.hemilineage_df = pd.read_csv(hemilineage_csv)
        return self.hemilineage_df

    def validate_dataset(self, progress_wrapper=None):
        """Checks if the dataset is complete by verifying required files.

        Args:
            progress_wrapper (callable, optional): A function like
                `napari.utils.progress` to wrap the iterator for progress
                tracking. Defaults to None.

        Returns:
            bool: True if all required files are found.

        Raises:
            FileNotFoundError: If a required file is missing.
        """
        suffixes = [
            "_registered_meshes.nrrd",  # whole neuron voxels
            "_CBF_registered_meshes.nrrd",  # longest cellbody fiber voxels
            "_hat_bundles.nrrd",  # hat bundles voxels
            "_hat_bundles.pkl",  # hat bundles dot probabilities for Nblast
        ]
        # To-do: update the naming system of the files

        iterable = self.hemilineage_list[0::10]
        if progress_wrapper:
            iterable = progress_wrapper(
                iterable,
                desc="Validating dataset:",
            )

        for i in iterable:
            for suffix in suffixes:
                file_path = self.fafb_root / i / f"{i}{suffix}"
                if not file_path.exists():
                    raise FileNotFoundError(
                        f"Dataset is not complete, missing {file_path}"
                    )

        print(f"All required files found in {self.fafb_root}.")
        return True

    def get_JRC2018U_mesh(self) -> Any:
        """Gets the JRC2018U brain mesh for plotting.

        Returns:
            Any: The loaded JRC2018U mesh data, typically a pickled object.

        Raises:
            FileNotFoundError: If the mesh file is not found.
        """
        JRC2018U_path = self.fafb_root / "flybrains.JRC2018U.mesh.pkl"
        if not JRC2018U_path.exists():
            raise FileNotFoundError(
                f"Dataset is not complete, missing {JRC2018U_path}"
            )
        with open(JRC2018U_path, "rb") as f:
            return pickle.load(f)

    def get_hemilineage_list(self) -> list[str]:
        """Gets the list of available hemilineages.

        Returns:
            list[str]: A list of hemilineage identifier strings.
        """
        return self.hemilineage_list

    def _get_data(self, hemilineage: str, suffix: str, file_type: str) -> Any:
        """A private helper to load data files securely.

        Args:
            hemilineage (str): The identifier for the hemilineage.
            suffix (str): The file suffix to identify the data type.
            file_type (str): The type of file to load ('nrrd' or 'pkl').

        Returns:
            Any: The loaded data, either a NumPy array or a pickled object.

        Raises:
            ValueError: If the hemilineage is not found or file type is unsupported.
            FileNotFoundError: If the required data file is not found.
        """
        if hemilineage not in self.hemilineage_list:
            raise ValueError(
                f"Hemilineage '{hemilineage}' not found in the dataset."
            )

        file_path = self.fafb_root / hemilineage / f"{hemilineage}{suffix}"

        if not file_path.exists():
            raise FileNotFoundError(f"Required file not found: {file_path}")

        if file_type == "nrrd":
            data, _ = nrrd.read(file_path)
            return np.transpose(data, (2, 1, 0))
        elif file_type == "pkl":
            with open(file_path, "rb") as f:
                return pickle.load(f)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def get_whole_neuron_nrrd(self, hemilineage: str) -> npt.NDArray[Any]:
        """Gets the whole neuron NRRD file for a specific hemilineage.

        Args:
            hemilineage (str): The identifier for the hemilineage.

        Returns:
            npt.NDArray[Any]: A NumPy array containing the voxel data.
        """
        return self._get_data(hemilineage, "_registered_meshes.nrrd", "nrrd")

    def get_cellbody_fiber_nrrd(self, hemilineage: str) -> npt.NDArray[Any]:
        """Gets the cell body fiber NRRD file for a specific hemilineage.

        Args:
            hemilineage (str): The identifier for the hemilineage.

        Returns:
            npt.NDArray[Any]: A NumPy array containing the voxel data.
        """
        return self._get_data(
            hemilineage, "_CBF_registered_meshes.nrrd", "nrrd"
        )

    def get_hat_bundles_nrrd(self, hemilineage: str) -> npt.NDArray[Any]:
        """Gets the hat bundles NRRD file for a specific hemilineage.

        Args:
            hemilineage (str): The identifier for the hemilineage.

        Returns:
            npt.NDArray[Any]: A NumPy array containing the voxel data.
        """
        return self._get_data(hemilineage, "_hat_bundles.nrrd", "nrrd")

    def get_hat_bundles_dps(
        self, hemilineage: str, symmetry: bool = False
    ) -> Any:
        """Gets the hat bundles dotprops for a specific hemilineage.

        Args:
            hemilineage (str): The identifier for the hemilineage.
            symmetry (bool): If True, loads the symmetrized dotprops.
                Defaults to False.

        Returns:
            Any: A navis `Dotprops` object representing the neuron skeleton.
        """
        if not symmetry:
            return self._get_data(hemilineage, "_hat_bundles.pkl", "pkl")
        else:
            return self._get_data(hemilineage, "_hat_bundles_sym.pkl", "pkl")


if __name__ == "__main__":
    test_fafb_path = (
        "/Volumes/lsa-mcdb-jclowney/lab/Computational_tools/FAFB_lineage"
    )
    loader = FAFB_loader(test_fafb_path)
    hemilineages = loader.get_hemilineage_list()
    print(hemilineages[13])
    whole_neuron = loader.get_whole_neuron_nrrd(hemilineages[13])
    print(whole_neuron.shape)
    cbf_neuron = loader.get_cellbody_fiber_nrrd(hemilineages[13])
    print(cbf_neuron.shape)
    hat_bundles = loader.get_hat_bundles_nrrd(hemilineages[13])
    print(hat_bundles.shape)
    hat_bundles_dps = loader.get_hat_bundles_dps(hemilineages[13])
    print(hat_bundles_dps)
    hat_bundles_dps_sym = loader.get_hat_bundles_dps(
        hemilineages[13], symmetry=True
    )
    print(hat_bundles_dps_sym)
