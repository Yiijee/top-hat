# src/top_hat/utils/qwidget_modules.py
from typing import TYPE_CHECKING

from napari.utils import progress
from napari.utils.notifications import show_error, show_info, show_warning
from qtpy.QtCore import QSettings, Qt, Signal
from qtpy.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..core.cellbody_matching import centroid_matching
from .data_loaders import FAFB_loader

if TYPE_CHECKING:
    import napari


class ConnectionWidget(QWidget):
    """A widget to handle FAFB dataset connection."""

    connected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.loader = None
        self.setLayout(QHBoxLayout())
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Enter path to FAFB dataset...")
        browse_btn = QPushButton("Browse")
        connect_btn = QPushButton("Connect")
        self.layout().addWidget(self.path_edit)
        self.layout().addWidget(browse_btn)
        self.layout().addWidget(connect_btn)

        browse_btn.clicked.connect(self._on_browse)
        connect_btn.clicked.connect(self._on_connect)

        self._load_settings()

    def _load_settings(self):
        """Load the last used data path from settings."""
        settings = QSettings("top-hat", "hat-viewer")
        last_path = settings.value("data_path", "")
        if last_path:
            self.path_edit.setText(last_path)

    def _save_settings(self):
        """Save the current data path to settings."""
        settings = QSettings("top-hat", "hat-viewer")
        settings.setValue("data_path", self.path_edit.text())

    def _on_connect(self):
        """Connect to the FAFB dataset path."""
        path = self.path_edit.text()
        if not path:
            show_warning("Please provide a path.")
            return

        try:
            self.loader = FAFB_loader(path)
            self.loader.validate_dataset(progress_wrapper=progress)
            show_info("Successfully connected to dataset!")
            self._save_settings()
            self.connected.emit(self.loader)
        except (FileNotFoundError, ValueError, NotADirectoryError) as e:
            show_error(f"Connection failed: {e}")
            self.loader = None
            self.connected.emit(None)

    def _on_browse(self):
        """Open a dialog to select the data directory."""
        path = QFileDialog.getExistingDirectory(
            self, "Select FAFB Dataset Directory"
        )
        if path:
            self.path_edit.setText(path)
            self._on_connect()


class SomaDetectionWidget(QWidget):
    """A widget for soma detection and centroid calculation."""

    def __init__(self, viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.viewer = viewer
        self.loader = None
        self.last_centroid = None
        self.last_matched_hemilineages = None

        self.setLayout(QVBoxLayout())

        # --- UI Setup ---
        self.info_label = QLabel(
            "Select points in the viewer to record (z, y, x) coordinates."
        )
        self.layout().addWidget(self.info_label)

        self.points_layer = self.viewer.add_points(
            name="Selected Points", ndim=3
        )
        self.points_layer.events.data.connect(self._on_points_added)

        self.centroid_btn = QPushButton("Get Cluster Centroid")
        self.centroid_btn.clicked.connect(self._get_cluster_centroid)
        self.layout().addWidget(self.centroid_btn)
        self.centroid_btn.setEnabled(False)  # Disabled until connected

    def set_loader(self, loader_instance):
        """Set the data loader and enable the widget."""
        self.loader = loader_instance
        self.centroid_btn.setEnabled(self.loader is not None)

    def _on_points_added(self, event):
        """Update point labels when data changes."""
        coords = self.points_layer.data
        labels = [str(i + 1) for i in range(len(coords))]
        self.points_layer.text = {"string": labels, "size": 2, "color": "red"}

    def _calculate_centroid(self, indices):
        """Return the centroid coordinates for selected indices."""
        coords = self.points_layer.data
        if len(coords) == 0 or not indices:
            return None
        selected_coords = coords[indices]
        return tuple(float(c) for c in selected_coords.mean(axis=0))

    def _get_cluster_centroid(self):
        """Get point indices from user, calculate centroid, and run matching."""
        if self.loader is None:
            show_warning("Please connect to a dataset first.")
            return

        coords = self.points_layer.data
        if len(coords) == 0:
            self.info_label.setText("No points selected.")
            return

        indices_str, ok = QInputDialog.getText(
            self,
            "Input Point Indices",
            "Enter point indices (e.g., 1,2,3 or 1-5) for centroid calculation:",
        )
        if not ok or not indices_str.strip():
            return

        try:
            indices = []
            for part in indices_str.split(","):
                part = part.strip()
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    indices.extend(range(start - 1, end))
                elif part:
                    indices.append(int(part) - 1)

            centroid_tuple = self._calculate_centroid(indices)
            if centroid_tuple is None:
                self.info_label.setText("No valid points for centroid.")
                return

            self.last_centroid = centroid_tuple
            self._update_viewer_with_centroid(centroid_tuple)

            user_centroid = centroid_tuple[::-1]  # Reverse for matching
            result = centroid_matching(user_centroid, self.loader)
            self.last_matched_hemilineages = result
            print(f"Matched hemilineages: {result['hemilineages']}")
            show_info(f"Matched hemilineages: {result['hemilineages']}")

        except (ValueError, IndexError) as e:
            show_error(f"Invalid input: {e}")
        # except Exception as e:
        #     show_error(f"An error occurred: {e}")

    def _update_viewer_with_centroid(self, centroid):
        """Add or update the centroid point layer in the viewer."""
        if "LM_centroid" in self.viewer.layers:
            self.viewer.layers["LM_centroid"].data = [centroid]
        else:
            self.viewer.add_points(
                [centroid],
                name="LM_centroid",
                size=15,
                face_color="yellow",
            )


class ThresholdWidget(QWidget):
    """A widget for image thresholding."""

    def __init__(self, viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.viewer = viewer
        self.is_initialized = False
        self.setLayout(QVBoxLayout())

        # --- UI Setup ---
        threshold_layout = QHBoxLayout()
        self.threshold_box = QLineEdit()
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_btn = QPushButton("Threshold")

        threshold_layout.addWidget(QLabel("Threshold:"))
        threshold_layout.addWidget(self.threshold_box)
        threshold_layout.addWidget(self.threshold_slider)
        self.layout().addLayout(threshold_layout)
        self.layout().addWidget(self.threshold_btn)

        # --- Initial State ---
        self.threshold_box.setEnabled(False)
        self.threshold_slider.setEnabled(False)

        # --- Connections ---
        self.threshold_btn.clicked.connect(self._on_threshold)

    def _initialize_threshold(self):
        """
        Initialize threshold controls based on 'query_image'.
        Returns True on success, False on failure.
        """
        try:
            query_layer = self.viewer.layers["query_image"]
            from skimage.filters import threshold_otsu

            threshold_value = threshold_otsu(query_layer.data)

            data_min, data_max = query_layer.data.min(), query_layer.data.max()
            self.threshold_slider.setRange(int(data_min), int(data_max))
            self.threshold_slider.setValue(int(threshold_value))
            self.threshold_box.setText(str(threshold_value))

            # Connect signals now that we are initialized
            self.threshold_slider.valueChanged.connect(
                lambda v: self.threshold_box.setText(str(v))
            )
            self.threshold_box.textChanged.connect(
                lambda t: self.threshold_slider.setValue(int(float(t)))
            )

            # Enable controls
            self.threshold_box.setEnabled(True)
            self.threshold_slider.setEnabled(True)
            self.is_initialized = True
            show_info("Threshold widget initialized.")
            return True

        except (KeyError, AttributeError):
            show_warning("Layer 'query_image' not found to initialize.")
            return False
        except ImportError:
            show_error("scikit-image is required for Otsu thresholding.")
            self.threshold_btn.setEnabled(False)  # Permanent failure
            return False
        except ValueError:
            # This can happen if the text box is empty or has non-numeric text
            # when textChanged signal is processed.
            # In our new flow, this is less likely but good to keep.
            return False

    def _on_threshold(self):
        """
        Initialize the widget if needed, then apply the threshold.
        """
        if not self.is_initialized and not self._initialize_threshold():
            return  # Initialization failed, so we stop.

        # If we reach here, the widget is initialized.
        try:
            threshold_value = float(self.threshold_box.text())
            query_layer = self.viewer.layers["query_image"]
            binarized_data = query_layer.data > threshold_value

            add_kwargs = {
                "name": "Binarized_Image",
                "axis_labels": ("x", "y", "z"),
                "scale": (0.38, 0.38, 0.38),
                "blending": "additive",
                "units": ("micron", "micron", "micron"),
            }
            if add_kwargs["name"] in self.viewer.layers:
                self.viewer.layers[add_kwargs["name"]].data = binarized_data
            else:
                self.viewer.add_image(
                    binarized_data, **add_kwargs, colormap="magenta"
                )
        except KeyError:
            show_error(
                "Could not find 'query_image' layer. "
                "Initialization may have failed."
            )
            self.is_initialized = False  # Reset state
            self.threshold_box.setEnabled(False)
            self.threshold_slider.setEnabled(False)
        except ValueError:
            show_error("Invalid threshold value.")
