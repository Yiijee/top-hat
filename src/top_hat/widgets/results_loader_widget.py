from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from napari.utils.notifications import show_error, show_warning
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    import napari


class ResultsLoaderWidget(QWidget):
    """A widget to load and manage matching results."""

    results_loaded = Signal(object, str)  # Emits DataFrame and file path

    def __init__(self, viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.viewer = viewer
        self.loader = None
        self.results_df = None
        self.results_path = (
            None  # This will be the actual or intended save path
        )
        self._required_columns = [
            "Hemilineage",
            "query_centroid",
            "time_stamp",
            "voxel_score",
            "nblast_score",
            "status",
            "threshold",
        ]

        self.setLayout(QVBoxLayout())

        # --- UI Setup ---
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(
            "Optional: Load a specific .csv file..."
        )
        browse_btn = QPushButton("Browse")
        load_btn = QPushButton("Load")

        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
        path_layout.addWidget(load_btn)

        self.status_label = QLabel("Status: Initializing...")
        self.status_label.setWordWrap(True)
        self.status_label.setMaximumWidth(350)

        self.layout().addLayout(path_layout)
        self.layout().addWidget(self.status_label)

        # --- Connections ---
        browse_btn.clicked.connect(self._on_browse)
        load_btn.clicked.connect(self._on_load)
        self.viewer.layers.events.inserted.connect(self._on_layers_changed)
        self.viewer.layers.events.removed.connect(self._on_layers_changed)

    def reset(self):
        """Reset the widget to its initial state."""
        self.path_edit.clear()
        self.status_label.setText("Status: Initializing...")
        self.results_df = None
        self.results_path = None
        self._on_layers_changed()

    def set_loader(self, loader_instance):
        """Set the data loader."""
        self.loader = loader_instance

    def perform_initial_load(self):
        """
        Perform the initial check for a query_image and load its results.
        This should be called after all signal/slot connections are established.
        """
        # --- Initial State ---
        # if self.results_df is None or self.results_df.empty:
        #     self._on_layers_changed()  # Check for existing query_image
        print("performing initial loading...")
        self.results_df = None
        self.results_path = None
        self._on_layers_changed()

    def _on_layers_changed(self, event=None):
        """
        Monitors layer changes to automatically find and load
        a corresponding results file.
        """
        print("Results loader: Layer changed detected...")
        try:
            query_layer = self.viewer.layers["query_image"]
            image_path_str = query_layer.metadata.get("path")
            if image_path_str:
                image_path = Path(image_path_str)
                results_path = image_path.with_name(
                    f"{image_path.stem}_results.csv"
                )
                # only load results if self.results_df is None or empty
                if self.results_df is None or self.results_df.empty:
                    print(
                        f"Results loader: Currently using empty DataFrame. Loading results from {results_path}"
                    )
                    self._load_file(results_path, is_manual_load=False)
            else:
                # query_image exists but has no path, so use empty df
                self._create_empty_df(update_status=True)
        except KeyError:
            # No query_image layer found
            self._create_empty_df(update_status=True)

    def _load_file(self, path: Path, is_manual_load: bool):
        """
        Load and validate a CSV file.
        - For auto-load, it sets the default save path even if the file doesn't exist.
        - For manual-load, it only loads if the file exists and is valid.
        """
        print(f"Results loader: Attempting to load file from {path}")
        final_df = None
        if path and path.exists():
            try:
                df_from_file = pd.read_csv(path)
                print(
                    f"Results loader: Loaded {len(df_from_file)} rows from {path}"
                )
                print(df_from_file.head(3))

                # Create a clean, complete dataframe but don't emit signal yet
                self._create_empty_df(
                    default_save_path=str(path), emit_signal=False
                )
                new_df = self.results_df.copy()
                self._update_status("Using default empty DataFrame.")

                # If loader wasn't ready, new_df is empty. Use file's hemilineages.
                if new_df.empty and "Hemilineage" in df_from_file.columns:
                    hemilineages = df_from_file["Hemilineage"].unique()
                    new_df = pd.DataFrame(
                        hemilineages, columns=["Hemilineage"]
                    )
                    # Re-apply default columns
                    for col in self._required_columns:
                        if col not in new_df.columns:
                            if col in [
                                "voxel_score",
                                "nblast_score",
                                "threshold",
                            ]:
                                new_df[col] = -1.0
                            elif col == "status":
                                new_df[col] = "not_reviewed"
                            else:
                                new_df[col] = ""
                    print(
                        "Results loader: FAFB loader is not ready. Loaded hemilineages from file."
                    )

                # Merge the loaded data into the new dataframe
                if "Hemilineage" in df_from_file.columns:
                    df_from_file.set_index("Hemilineage", inplace=True)
                    new_df.set_index("Hemilineage", inplace=True)

                    cols_to_update = [
                        "query_centroid",
                        "time_stamp",
                        "voxel_score",
                        "nblast_score",
                        "status",
                        "threshold",
                    ]
                    for col in cols_to_update:
                        if col in df_from_file.columns:
                            new_df.update(df_from_file[[col]])

                    new_df.reset_index(inplace=True)
                    self._update_status(f"Loaded: ...{Path(path).name}")
                    print(
                        f"Results loader: Successfully merged data from {path.name}"
                    )

                final_df = new_df
                self.results_path = str(path)

            except (OSError, pd.errors.ParserError) as e:
                show_error(f"Failed to read '{path.name}': {e}")
                if is_manual_load:
                    self._update_status(f"Error: Could not read {path.name}")
                self._create_empty_df(
                    default_save_path=str(path), emit_signal=False
                )
                final_df = self.results_df

        else:  # Path does not exist
            if is_manual_load:
                show_warning(f"File not found: {path}")
                self._update_status("Error: File not found at specified path.")
            self._create_empty_df(
                default_save_path=str(path), emit_signal=False
            )
            final_df = self.results_df

        # Emit the final, processed dataframe
        self.results_df = final_df
        self.results_loaded.emit(self.results_df, self.results_path)

    def _create_empty_df(
        self, default_save_path=None, update_status=False, emit_signal=True
    ):
        """
        Create a DataFrame with all hemilineages, initializing columns.
        """
        if self.loader:
            hemilineages = self.loader.hemilineage_list
            df = pd.DataFrame(hemilineages, columns=["Hemilineage"])
            df["query_centroid"] = ""
            df["time_stamp"] = ""
            df["voxel_score"] = -1.0
            df["nblast_score"] = -1.0
            df["status"] = "not_reviewed"
            df["threshold"] = -1.0
            self.results_df = df
        else:
            self.results_df = pd.DataFrame(columns=self._required_columns)

        self.results_path = default_save_path
        if update_status:
            self._update_status("Created a new, empty results table.")

        if emit_signal:
            self.results_loaded.emit(self.results_df, self.results_path)

    def _update_status(self, message: str):
        """Updates the status label."""
        self.status_label.setText(f"Status: {message}")

    def _on_browse(self):
        """Open a file dialog to select a results file."""
        default_dir = ""
        try:
            query_layer = self.viewer.layers["query_image"]
            image_path_str = query_layer.metadata.get("path")
            if image_path_str:
                default_dir = str(Path(image_path_str).parent)
        except KeyError:
            pass  # No query image, so use default directory

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Results CSV", default_dir, "CSV Files (*.csv)"
        )
        if path:
            self.path_edit.setText(path)
            self._on_load()

    def _on_load(self):
        """Load the file specified in the path edit box (manual override)."""
        path_str = self.path_edit.text()
        if path_str:
            self._load_file(Path(path_str), is_manual_load=True)
        else:
            show_warning("Please specify a file path to load.")
            self._update_status("Specify a file path to manually load.")

    def get_results_df(self):
        """Return the currently loaded DataFrame."""
        return self.results_df

    def get_results_path(self):
        """Return the path of the loaded results file."""
        return self.results_path
