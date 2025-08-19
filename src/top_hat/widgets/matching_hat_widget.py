from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from napari.utils.notifications import show_error, show_info, show_warning
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.hat_NBLAST import hat_nblast
from ..core.voxel_counting import count_voxels_in_hemilineage
from ..utils.colors import generate_random_hex_color
from .soma_detection_widget import SomaDetectionWidget

if TYPE_CHECKING:
    import napari


class MatchingHatWidget(QWidget):
    """A widget for matching query images with hemilineage templates."""

    def __init__(
        self,
        viewer: "napari.viewer.Viewer",
        soma_detection_widget: "SomaDetectionWidget",
        parent=None,
    ):
        super().__init__(parent)
        self.viewer = viewer
        self.soma_detection_widget = soma_detection_widget
        self.loader = None
        self.results = {}
        self.results_df = None
        self.results_path = None

        self.setLayout(QVBoxLayout())

        # --- UI Setup ---
        self.hemilineage_input = QTextEdit()
        self.hemilineage_input.setPlaceholderText(
            "Enter hemilineage names, one per line..."
        )
        self.hemilineage_input.setFixedHeight(100)

        checkbox_layout = QHBoxLayout()
        self.voxel_checkbox = QCheckBox("Voxel Counting")
        self.nblast_checkbox = QCheckBox("NBLAST")
        self.voxel_checkbox.setChecked(True)
        self.nblast_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.voxel_checkbox)
        checkbox_layout.addWidget(self.nblast_checkbox)

        self.match_button = QPushButton("Match")
        self.update_display_button = QPushButton("Update Display")
        self.save_button = QPushButton("Save Selected")
        # self.test_populate_button = QPushButton("Test Populate")

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.match_button)
        button_layout.addWidget(self.update_display_button)
        button_layout.addWidget(self.save_button)
        # button_layout.addWidget(self.test_populate_button)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(
            ["Hemilineage", "Voxel", "NBLAST", "Tract", "Whole", "Save"]
        )
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.layout().addWidget(self.hemilineage_input)
        self.layout().addLayout(checkbox_layout)
        self.layout().addLayout(button_layout)
        self.layout().addWidget(self.results_table)

        # --- Connections ---
        self.match_button.clicked.connect(self._on_match)
        self.save_button.clicked.connect(self._on_save)
        self.update_display_button.clicked.connect(self._on_update_display)
        # self.test_populate_button.clicked.connect(self._on_test_populate)

        self.viewer.layers.events.inserted.connect(self._on_layers_changed)
        self.viewer.layers.events.removed.connect(self._on_layers_changed)
        self._update_enabled_state()

    def reset(self):
        """Reset the widget for a new query image."""
        self.hemilineage_input.clear()
        self.results.clear()
        self._populate_table()

    def _update_enabled_state(self):
        """Enable/disable widget based on dependencies."""
        binarized_image_exists = "binarized_image" in self.viewer.layers
        enabled = all(
            [
                self.loader is not None,
                self.results_df is not None,
                binarized_image_exists,
            ]
        )
        self.match_button.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
        self.update_display_button.setEnabled(enabled)
        self.hemilineage_input.setEnabled(enabled)

    def _on_layers_changed(self, event):
        """Respond to changes in viewer layers."""
        self._update_enabled_state()

    def set_loader(self, loader_instance):
        """Set the data loader."""
        self.loader = loader_instance
        self._update_enabled_state()

    def set_hemilineages(self, hemilineages):
        """Set the hemilineage input text."""
        self.hemilineage_input.setText("\n".join(hemilineages))

    def _on_save(self):
        """
        Save rows with a checked "Save" box to the results file.
        """
        if self.results_path is None or self.results_df is None:
            show_warning("No results file loaded to save to.")
            return

        if self.soma_detection_widget.manual_centroid is None:
            show_warning(
                "Query centroid not set. Please create a point in the 'matched_points' layer."
            )
            return

        new_data = []
        rows_to_save = []
        for row_idx in range(self.results_table.rowCount()):
            save_item = self.results_table.item(row_idx, 5)  # 'Save' checkbox
            if save_item and save_item.checkState() == Qt.Checked:
                rows_to_save.append(row_idx)

        if not rows_to_save:
            show_warning("No rows checked to save.")
            return

        for row in rows_to_save:
            hemilineage = self.results_table.item(row, 0).text()

            # Skip if already in the permanent DataFrame
            if hemilineage in self.results_df["Hemilineage"].values:
                continue

            voxel_item = self.results_table.item(row, 1)
            nblast_item = self.results_table.item(row, 2)

            new_data.append(
                {
                    "Hemilineage": hemilineage,
                    "voxel_score": (
                        float(voxel_item.text())
                        if voxel_item and voxel_item.text()
                        else -1
                    ),
                    "nblast_score": (
                        float(nblast_item.text())
                        if nblast_item and nblast_item.text()
                        else -1
                    ),
                    "query_centroid": self.soma_detection_widget.manual_centroid,
                    "time_stamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        if not new_data:
            show_info(
                "All checked hemilineages have already been saved in a previous session."
            )
            return

        new_df = pd.DataFrame(new_data)
        updated_df = pd.concat([self.results_df, new_df], ignore_index=True)
        try:
            updated_df.to_csv(self.results_path, index=False)
            self.results_df = updated_df  # Update internal state
            show_info(
                f"Saved {len(new_data)} new results to {Path(self.results_path).name}"
            )
            # Clear the staging table
            self.results.clear()
            self._populate_table()
        except OSError as e:
            show_error(f"Failed to save results: {e}")

    def _on_results_loaded(self, results_df, results_path):
        self.results_df = results_df
        self.results_path = results_path
        self._update_enabled_state()

    def _on_match(self, progress):
        # Clear previous temporary results
        self.results.clear()
        self._populate_table()

        if self.loader is None:
            show_warning("Please connect to a dataset first.")
            return
        if self.results_df is None:
            show_warning("Please load a results file first.")
            return

        hemilineages = self.hemilineage_input.toPlainText().strip().split("\n")
        hemilineages = [h.strip() for h in hemilineages if h.strip()]
        # exclude hemilineages not in hemilineage list
        hemilineages = [
            h for h in hemilineages if h in self.loader.hemilineage_list
        ]

        # Exclude hemilineages that are already in the results table
        existing_hemilineages = self.results_df["Hemilineage"].tolist()
        hemilineages_to_run = [
            h for h in hemilineages if h not in existing_hemilineages
        ]

        if not hemilineages_to_run:
            show_info("All specified hemilineages have already been matched.")
            return

        new_results = {
            h: {"voxel": -1, "nblast": -1} for h in hemilineages_to_run
        }

        # Run Voxel Counting
        if self.voxel_checkbox.isChecked():
            try:
                query_layer = self.viewer.layers["binarized_image"]
                voxel_scores = count_voxels_in_hemilineage(
                    query_layer.data,
                    hemilineages_to_run,
                    self.loader,
                    progress_wrapper=progress,
                )
                for h, score in voxel_scores.items():
                    new_results[h]["voxel"] = score
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
                    hemilineages_to_run,
                    threshold,
                    self.loader,
                    progress_wrapper=progress,
                )
                for h, nblast_score in nblast_scores.items():
                    new_results[h]["nblast"] = nblast_score

            except KeyError:
                show_error("Query image not found for NBLAST.")
            # except Exception as e:
            #     show_error(f"NBLAST failed: {e}")

        # Set the new results to be displayed in the staging table
        self.results = new_results
        self._populate_table()

    def _populate_table(self):
        """Fill the results table with matching scores."""
        self.results_table.setSortingEnabled(False)  # Disable sorting
        self.results_table.setRowCount(0)  # Clear rows, keep headers
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

    # def _on_test_populate(self):
    #     """Generate pseudo-data to test table population."""
    #     import random

    #     pseudo_results = {}
    #     hemilineages = [
    #         "00B",
    #         "01A",
    #         "01B",
    #         "02A",
    #         "02B",
    #         "03A",
    #         "03B",
    #         "04A",
    #         "04B",
    #         "05A",
    #     ]
    #     for h in hemilineages:
    #         pseudo_results[h] = {
    #             "voxel": random.uniform(0, 100),
    #             "nblast": random.uniform(-1, 1),
    #         }
    #     self.results = pseudo_results
    #     self._populate_table()
    #     show_info("Populated table with pseudo-data.")
