from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from napari.utils.notifications import show_error, show_info, show_warning
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
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
        self.results_df = None
        self.results_path = None
        self.last_matched_hemilineages = []

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
        self.save_button = QPushButton("Save Results")

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.match_button)
        button_layout.addWidget(self.update_display_button)
        button_layout.addWidget(self.save_button)

        self.show_recent_only_checkbox = QCheckBox(
            "Show only most recent results"
        )

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(
            [
                "Hemilineage",
                "Voxel",
                "NBLAST",
                "Tract",
                "Neuron",
                "Status",
            ]
        )
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.layout().addWidget(self.hemilineage_input)
        self.layout().addLayout(checkbox_layout)
        self.layout().addLayout(button_layout)
        self.layout().addWidget(self.show_recent_only_checkbox)
        self.layout().addWidget(self.results_table)

        # --- Connections ---
        self.match_button.clicked.connect(self._on_match)
        self.save_button.clicked.connect(self._on_save)
        self.update_display_button.clicked.connect(self._on_update_display)
        self.show_recent_only_checkbox.toggled.connect(self._on_display_toggle)

        self.viewer.layers.events.inserted.connect(self._on_layers_changed)
        self.viewer.layers.events.removed.connect(self._on_layers_changed)
        self._update_enabled_state()

    def reset(self):
        """Reset the widget for a new query image."""
        self.hemilineage_input.clear()
        self.last_matched_hemilineages = []
        self.show_recent_only_checkbox.setChecked(False)
        if self.results_df is not None:
            self.results_df = None
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
        self.show_recent_only_checkbox.setEnabled(
            enabled and bool(self.last_matched_hemilineages)
        )

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

    def _on_display_toggle(self):
        """Handle the toggle switch for the results display."""
        self._on_save()
        self._populate_table()

    def _on_save(self):
        """
        Update the results DataFrame with the current statuses from the table
        and save it to the CSV file.
        """
        if self.results_path is None or self.results_df is None:
            show_warning("No results file available to save.")
            return

        # Update the DataFrame from the table
        for row_idx in range(self.results_table.rowCount()):
            hemilineage_item = self.results_table.item(row_idx, 0)
            if not hemilineage_item:
                continue
            hemilineage = hemilineage_item.text()
            status_combo = self.results_table.cellWidget(row_idx, 5)
            if status_combo:
                status = status_combo.currentText()
                self.results_df.loc[
                    self.results_df["Hemilineage"] == hemilineage, "status"
                ] = status

        try:
            self.results_df.to_csv(self.results_path, index=False)
            show_info(
                f"Successfully saved results to {Path(self.results_path).name}"
            )
        except OSError as e:
            show_error(f"Failed to save results: {e}")

    def _on_results_loaded(self, results_df, results_path):
        self.results_df = results_df
        self.results_path = results_path
        self.last_matched_hemilineages = []
        self.show_recent_only_checkbox.setChecked(False)
        self._update_enabled_state()
        self._populate_table()

    def _on_match(self, progress):
        if self.loader is None:
            show_warning("Please connect to a dataset first.")
            return
        if self.results_df is None:
            show_warning("Please load a results file first.")
            return
        if self.soma_detection_widget.manual_centroid is None:
            show_warning("Please set a query centroid first.")
            return

        try:
            query_layer = self.viewer.layers["query_image"]
            binarized_layer = self.viewer.layers["binarized_image"]
            current_threshold = binarized_layer.metadata.get("threshold")
        except KeyError:
            show_error(
                "Required layers ('query_image', 'binarized_image') not found."
            )
            return

        hemilineages_to_process = (
            self.hemilineage_input.toPlainText().strip().split("\n")
        )
        hemilineages_to_process = [
            h.strip() for h in hemilineages_to_process if h.strip()
        ]
        if not hemilineages_to_process:
            show_info("No hemilineages specified to match.")
            return
        # track recent hemilineage input
        self.last_matched_hemilineages = hemilineages_to_process
        print(f"last matched hemilineages: {self.last_matched_hemilineages}")
        self.show_recent_only_checkbox.setChecked(True)
        self._update_enabled_state()
        # Filter for hemilineages that need matching
        hemilineages_to_run = []
        for h in hemilineages_to_process:
            row = self.results_df[self.results_df["Hemilineage"] == h]
            if not row.empty:
                has_score = (
                    row["voxel_score"].iloc[0] != -1
                    or row["nblast_score"].iloc[0] != -1
                )
                threshold_changed = (
                    row["threshold"].iloc[0] != current_threshold
                )
                if not has_score or threshold_changed:
                    hemilineages_to_run.append(h)
            else:
                hemilineages_to_run.append(
                    h
                )  # Should not happen with new logic

        if not hemilineages_to_run:
            show_info("All specified hemilineages have up-to-date scores.")
            self._populate_table()
            return

        # Run Voxel Counting
        if self.voxel_checkbox.isChecked():
            try:
                voxel_scores = count_voxels_in_hemilineage(
                    binarized_layer.data,
                    hemilineages_to_run,
                    self.loader,
                    progress_wrapper=progress,
                )
                for h, score in voxel_scores.items():
                    self.results_df.loc[
                        self.results_df["Hemilineage"] == h, "voxel_score"
                    ] = score
            except KeyError as e:
                show_error(f"Voxel counting failed: {e}")

        # Run NBLAST
        if self.nblast_checkbox.isChecked():
            try:
                query_image_path = query_layer.metadata.get("path")
                if not query_image_path:
                    show_warning("Query image path not found for NBLAST.")
                else:
                    nblast_scores = hat_nblast(
                        query_image_path,
                        hemilineages_to_run,
                        current_threshold,
                        self.loader,
                        progress_wrapper=progress,
                    )
                    for h, score in nblast_scores.items():
                        self.results_df.loc[
                            self.results_df["Hemilineage"] == h, "nblast_score"
                        ] = score
            except KeyError as e:
                show_error(f"NBLAST failed: {e}")

        # Update metadata for all matched hemilineages
        time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for h in hemilineages_to_run:
            self.results_df.loc[
                self.results_df["Hemilineage"] == h, "query_centroid"
            ] = str(self.soma_detection_widget.manual_centroid)
            self.results_df.loc[
                self.results_df["Hemilineage"] == h, "time_stamp"
            ] = time_stamp
            self.results_df.loc[
                self.results_df["Hemilineage"] == h, "threshold"
            ] = current_threshold

        show_info(
            f"Matching complete for {len(hemilineages_to_run)} hemilineages."
        )
        # save results once before populating table
        self._on_save()
        self._populate_table()

    def _populate_table(self):
        """Fill the results table from the results DataFrame."""
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(0)

        if self.results_df is None:
            return

        if (
            self.show_recent_only_checkbox.isChecked()
            and self.last_matched_hemilineages
        ):
            df_to_display = self.results_df[
                self.results_df["Hemilineage"].isin(
                    self.last_matched_hemilineages
                )
            ].copy()
            df_to_display.reset_index(inplace=True)
            print("Displaying recent matching results:")
            print(df_to_display.head())
        else:
            df_to_display = self.results_df

        self.results_table.setRowCount(len(df_to_display))

        for row_idx, row_data in df_to_display.iterrows():
            name = row_data["Hemilineage"]
            self.results_table.setItem(row_idx, 0, QTableWidgetItem(name))

            # Voxel Score
            voxel_score = row_data["voxel_score"]
            if pd.notna(voxel_score) and voxel_score != -1:
                voxel_item = QTableWidgetItem(f"{voxel_score:.4f}")
                voxel_item.setData(Qt.UserRole, voxel_score)
            else:
                voxel_item = QTableWidgetItem("")
            self.results_table.setItem(row_idx, 1, voxel_item)

            # NBLAST Score
            nblast_score = row_data["nblast_score"]
            if pd.notna(nblast_score) and nblast_score != -1:
                nblast_item = QTableWidgetItem(f"{nblast_score:.4f}")
                nblast_item.setData(Qt.UserRole, nblast_score)
            else:
                nblast_item = QTableWidgetItem("")
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

            # Status Dropdown
            status_combo = QComboBox()
            status_combo.addItems(
                ["unsure", "accept", "reject", "not_reviewed"]
            )
            current_status = row_data.get("status", "not_reviewed")
            status_combo.setCurrentText(current_status)
            self.results_table.setCellWidget(row_idx, 5, status_combo)

        self.results_table.setSortingEnabled(True)
        self.results_table.sortByColumn(2, Qt.DescendingOrder)
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.results_table.resizeColumnsToContents()

    def _on_update_display(self):
        """Load selected tracts and neurons into the viewer."""
        if not self.loader:
            show_warning("Data loader not available.")
            return

        selected_hemilineages = []
        for row_idx in range(self.results_table.rowCount()):
            tract_item = self.results_table.item(row_idx, 3)
            neuron_item = self.results_table.item(row_idx, 4)
            if (
                tract_item.checkState() == Qt.Checked
                or neuron_item.checkState() == Qt.Checked
            ):
                hemilineage_name = self.results_table.item(row_idx, 0).text()
                selected_hemilineages.append(
                    (
                        hemilineage_name,
                        tract_item.checkState() == Qt.Checked,
                        neuron_item.checkState() == Qt.Checked,
                    )
                )

        if not selected_hemilineages:
            show_info("No hemilineages selected for display.")
            return

        for name, load_tract, load_neuron in selected_hemilineages:
            if load_tract:
                tracts = self.loader.get_hat_bundles_nrrd(name)
                layer_name = f"{name}_tract"
                layer_kwargs = {
                    "name": layer_name,
                    "axis_labels": ("x", "y", "z"),
                    "blending": "additive",
                    "contrast_limits": [0, 1],
                    "colormap": generate_random_hex_color(),
                    "scale": (0.38, 0.38, 0.38),
                    "units": ("micron", "micron", "micron"),
                    "metadata": {"hemilineage": name},
                }
                if layer_kwargs["name"] in self.viewer.layers:
                    self.viewer.layers[layer_kwargs["name"]].data = tracts
                else:
                    self.viewer.add_image(tracts, **layer_kwargs)
            if load_neuron:
                neurons = self.loader.get_whole_neuron_nrrd(name)
                layer_name = f"{name}_neurons"
                layer_kwargs = {
                    "name": layer_name,
                    "axis_labels": ("x", "y", "z"),
                    "blending": "additive",
                    "contrast_limits": [0, 1],
                    "colormap": generate_random_hex_color(),
                    "scale": (0.38, 0.38, 0.38),
                    "units": ("micron", "micron", "micron"),
                    "metadata": {"hemilineage": name},
                }
                if layer_kwargs["name"] in self.viewer.layers:
                    self.viewer.layers[layer_kwargs["name"]].data = neurons
                else:
                    self.viewer.add_image(neurons, **layer_kwargs)
