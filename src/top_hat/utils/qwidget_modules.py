# src/top_hat/utils/qwidget_modules.py
from typing import TYPE_CHECKING

from napari.utils import progress
from napari.utils.notifications import show_error, show_info, show_warning
from qtpy.QtCore import QSettings, Qt, Signal
from qtpy.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.cellbody_matching import centroid_matching
from ..core.hat_NBLAST import hat_nblast
from ..core.voxel_counting import count_voxels_in_hemilineage
from .colors import generate_random_hex_color
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

    matched = Signal(list)

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
        self.points_layer.text = {"string": labels, "size": 7, "color": "red"}
        self.points_layer.size = 5

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
            self.last_matched_hemilineages = result["hemilineages"]
            self.matched.emit(self.last_matched_hemilineages)
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
                "name": "binarized_image",
                "axis_labels": ("x", "y", "z"),
                "scale": (0.38, 0.38, 0.38),
                "blending": "additive",
                "units": ("micron", "micron", "micron"),
                "metadata": {"threshold": threshold_value},
            }
            if add_kwargs["name"] in self.viewer.layers:
                self.viewer.layers[add_kwargs["name"]].data = binarized_data
                self.viewer.layers[add_kwargs["name"]].metadata[
                    "threshold"
                ] = threshold_value
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


class MatchingHatWidget(QWidget):
    """A widget for matching against hemilineages."""

    def __init__(self, viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.viewer = viewer
        self.loader = None
        self.results = {}  # To store matching scores

        self.setLayout(QVBoxLayout())

        # --- UI Setup ---
        # 1. Hemilineage Input
        self.layout().addWidget(QLabel("Hemilineages to Match:"))
        self.hemilineage_input = QTextEdit()
        self.hemilineage_input.setPlaceholderText(
            "Enter hemilineage names, one per line..."
        )
        self.layout().addWidget(self.hemilineage_input)

        # 2. Matching Method Selection
        method_layout = QHBoxLayout()
        self.voxel_checkbox = QCheckBox("Voxel Counting")
        self.nblast_checkbox = QCheckBox("NBLAST")
        self.nblast_checkbox.setChecked(True)  # Default
        method_layout.addWidget(self.voxel_checkbox)
        method_layout.addWidget(self.nblast_checkbox)
        self.layout().addLayout(method_layout)

        # 3. Action Buttons
        action_layout = QHBoxLayout()
        self.match_btn = QPushButton("Match")
        self.update_display_btn = QPushButton("Update Display")
        self.save_btn = QPushButton("Save Results")
        action_layout.addWidget(self.match_btn)
        action_layout.addWidget(self.update_display_btn)
        action_layout.addWidget(self.save_btn)
        self.layout().addLayout(action_layout)

        # 4. Results Table
        self.results_table = QTableWidget()
        self.layout().addWidget(self.results_table)

        # --- Connections ---
        self.match_btn.clicked.connect(self._on_match)
        self.update_display_btn.clicked.connect(self._on_update_display)

    def set_loader(self, loader_instance):
        """Set the data loader."""
        self.loader = loader_instance
        self.match_btn.setEnabled(self.loader is not None)

    def set_hemilineages(self, hemilineages: list[str]):
        """Set the hemilineages in the input box."""
        self.hemilineage_input.setText("\n".join(hemilineages))

    def _on_match(self):
        """Run the selected matching algorithms."""
        if not self.loader:
            show_warning("Please connect to a dataset first.")
            return

        hemilineages = self.hemilineage_input.toPlainText().strip().split("\n")
        hemilineages = [h.strip() for h in hemilineages if h.strip()]
        # exclude hemilineages not in hemilineage list
        hemilineages = [
            h for h in hemilineages if h in self.loader.hemilineage_list
        ]
        if not hemilineages:
            show_warning("Please enter at least one hemilineage.")
            return

        self.results = {h: {"voxel": -1, "nblast": -1} for h in hemilineages}

        # Run Voxel Counting
        if self.voxel_checkbox.isChecked():
            try:
                query_layer = self.viewer.layers["binarized_image"]
                voxel_scores = count_voxels_in_hemilineage(
                    query_layer.data,
                    hemilineages,
                    self.loader,
                    progress_wrapper=progress,
                )
                for h, score in voxel_scores.items():
                    self.results[h]["voxel"] = score
            except KeyError:
                show_error("Binarized image not found for Voxel Counting.")
            # except Exception as e:
            #     show_error(f"Voxel counting failed: {e}")

        # Run NBLAST
        if self.nblast_checkbox.isChecked():
            try:
                query_image_path = self.viewer.layers[
                    "query_image"
                ].metadata.get("path")
                threshold = self.viewer.layers["binarized_image"].metadata.get(
                    "threshold"
                )
                if not query_image_path:
                    show_warning("Query image path not found.")
                    return
                # run NBLAST
                nblast_scores = hat_nblast(
                    query_image_path,
                    hemilineages,
                    threshold,
                    self.loader,
                    progress_wrapper=progress,
                )
                for h, nblast_score in nblast_scores.items():
                    self.results[h]["nblast"] = nblast_score

            except KeyError:
                show_error("Query image not found for NBLAST.")
            # except Exception as e:
            #     show_error(f"NBLAST failed: {e}")

        self._populate_table()

    def _populate_table(self):
        """Fill the results table with matching scores."""
        self.results_table.clear()
        headers = ["Hemilineage", "Voxel", "NBLAST", "Tract", "Whole", "Save"]
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        self.results_table.setRowCount(len(self.results))

        for row_idx, (name, scores) in enumerate(self.results.items()):
            # Name
            self.results_table.setItem(row_idx, 0, QTableWidgetItem(name))

            # Voxel Score
            voxel_score = scores.get("voxel")
            if voxel_score is not None:
                voxel_item = QTableWidgetItem(str(round(voxel_score, 4)))
                # Set data for numeric sorting
                voxel_item.setData(Qt.UserRole, voxel_score)
            else:
                voxel_item = QTableWidgetItem("")  # Empty item
            self.results_table.setItem(row_idx, 1, voxel_item)

            # NBLAST Score
            nblast_score = scores.get("nblast")
            if nblast_score is not None:
                nblast_item = QTableWidgetItem(str(round(nblast_score, 4)))
                # Set data for numeric sorting
                nblast_item.setData(Qt.UserRole, nblast_score)
            else:
                nblast_item = QTableWidgetItem("")  # Empty item
            self.results_table.setItem(row_idx, 2, nblast_item)

            # Tract Checkbox
            tract_check = QTableWidgetItem()
            tract_check.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            tract_check.setCheckState(Qt.Unchecked)
            self.results_table.setItem(row_idx, 3, tract_check)

            # Neuron Checkbox
            neuron_check = QTableWidgetItem()
            neuron_check.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            neuron_check.setCheckState(Qt.Unchecked)
            self.results_table.setItem(row_idx, 4, neuron_check)

            # Save Checkbox
            save_check = QTableWidgetItem()
            save_check.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            save_check.setCheckState(Qt.Unchecked)
            self.results_table.setItem(row_idx, 5, save_check)

        self.results_table.setSortingEnabled(True)
        # Default sort by NBLAST score, descending
        self.results_table.sortByColumn(2, Qt.DescendingOrder)

        # # Check top 5 tracts by default after sorting
        # Let the user check the boxes by them selfs
        # for i in range(min(5, self.results_table.rowCount())):
        #     self.results_table.item(i, 3).setCheckState(Qt.Checked)

        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.results_table.resizeColumnsToContents()

    def _on_update_display(self):
        """Load selected tracts and neurons into the viewer."""
        if not self.loader:
            show_warning("Please connect to a dataset first.")
            return

        for row_idx in range(self.results_table.rowCount()):
            hemilineage = self.results_table.item(row_idx, 0).text()
            is_tract_checked = (
                self.results_table.item(row_idx, 3).checkState() == Qt.Checked
            )
            is_neuron_checked = (
                self.results_table.item(row_idx, 4).checkState() == Qt.Checked
            )

            if is_tract_checked:
                tracts = self.loader.get_hat_bundles_nrrd(hemilineage)
                layer_name = f"{hemilineage}_tract"
                layer_kwargs = {
                    "name": layer_name,
                    "axis_labels": ("x", "y", "z"),
                    "blending": "additive",
                    "contrast_limits": [0, 1],
                    "colormap": generate_random_hex_color(),
                    "scale": (0.38, 0.38, 0.38),
                    "units": ("micron", "micron", "micron"),
                    "metadata": {"hemilineage": hemilineage},
                }
                if layer_kwargs["name"] in self.viewer.layers:
                    self.viewer.layers[layer_kwargs["name"]].data = tracts
                else:
                    self.viewer.add_image(tracts, **layer_kwargs)

            if is_neuron_checked:
                neurons = self.loader.get_whole_neuron_nrrd(hemilineage)
                layer_name = f"{hemilineage}_neurons"
                layer_kwargs = {
                    "name": layer_name,
                    "axis_labels": ("x", "y", "z"),
                    "blending": "additive",
                    "contrast_limits": [0, 1],
                    "colormap": generate_random_hex_color(),
                    "scale": (0.38, 0.38, 0.38),
                    "units": ("micron", "micron", "micron"),
                    "metadata": {"hemilineage": hemilineage},
                }
                if layer_kwargs["name"] in self.viewer.layers:
                    self.viewer.layers[layer_kwargs["name"]].data = neurons
                else:
                    self.viewer.add_image(neurons, **layer_kwargs)
