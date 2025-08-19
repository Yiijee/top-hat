from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from napari.utils.notifications import show_error, show_info, show_warning
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

        self.layout().addLayout(path_layout)
        self.layout().addWidget(self.status_label)

        # --- Connections ---
        browse_btn.clicked.connect(self._on_browse)
        load_btn.clicked.connect(self._on_load)
        self.viewer.layers.events.inserted.connect(self._on_layers_changed)
        self.viewer.layers.events.removed.connect(self._on_layers_changed)

    def perform_initial_load(self):
        """
        Perform the initial check for a query_image and load its results.
        This should be called after all signal/slot connections are established.
        """
        # --- Initial State ---
        self._on_layers_changed()  # Check for existing query_image
        if self.results_df is None:
            self._create_empty_df(update_status=True)

    def _on_layers_changed(self, event=None):
        """
        Monitors layer changes to automatically find and load
        a corresponding results file.
        """
        try:
            query_layer = self.viewer.layers["query_image"]
            image_path_str = query_layer.metadata.get("path")
            if image_path_str:
                image_path = Path(image_path_str)
                results_path = image_path.with_name(
                    f"{image_path.stem}_results.csv"
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
        if path and path.exists():
            try:
                df = pd.read_csv(path)
                # Validate columns
                if all(col in df.columns for col in self._required_columns):
                    self.results_df = df
                    self.results_path = str(path)
                    show_info(f"Successfully loaded results from {path.name}")
                    self._update_status(f"Loaded: ...{Path(path).name}")
                    self.results_loaded.emit(
                        self.results_df, self.results_path
                    )
                else:  # File exists but is invalid
                    show_warning(f"'{path.name}' has incorrect columns.")
                    if is_manual_load:
                        # Don't change state on manual load of bad file
                        self._update_status(
                            f"Error: Invalid columns in {path.name}"
                        )
                    else:
                        # Auto-load found a bad file, treat as if not found
                        self._create_empty_df(default_save_path=str(path))
            except (OSError, pd.errors.ParserError) as e:  # Error reading file
                show_error(f"Failed to read '{path.name}': {e}")
                if is_manual_load:
                    self._update_status(f"Error: Could not read {path.name}")
                else:
                    self._create_empty_df(default_save_path=str(path))
        else:  # Path does not exist
            if is_manual_load:
                show_warning(f"File not found: {path}")
                self._update_status("Error: File not found at specified path.")
            else:
                # This is the auto-load case where no results file exists yet.
                # We create an empty DF but set the *intended* save path.
                self._create_empty_df(default_save_path=str(path))

    def _create_empty_df(self, default_save_path=None, update_status=False):
        """
        Create an empty DataFrame. Can set a default save path and optionally
        update the status, which is suppressed during intermediate steps.
        """
        self.results_df = pd.DataFrame(columns=self._required_columns)
        self.results_path = default_save_path
        if update_status:
            self._update_status("Using empty results table.")

        # Always emit so other widgets know the state has changed
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
