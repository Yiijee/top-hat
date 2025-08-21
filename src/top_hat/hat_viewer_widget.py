from typing import TYPE_CHECKING

from napari.utils import progress
from napari.utils.notifications import show_error, show_info, show_warning
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .utils.colors import generate_random_hex_color
from .utils.plotter import plot_tracts
from .widgets import ConnectionWidget, ResultsLoaderWidget

if TYPE_CHECKING:
    import napari


class HatViewer(QWidget):
    """
    A napari widget for loading and visualizing FAFB hemilineage data.
    """

    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer
        self.loader = None
        self.results_df = None
        self.added_layers = []

        # --- UI Setup ---
        self.setLayout(QVBoxLayout())

        # 1. Data Connection
        self.connection_widget = ConnectionWidget()
        self.layout().addWidget(self.connection_widget)

        # 2. Results Loader
        self.results_loader_widget = ResultsLoaderWidget(self.viewer)
        self.layout().addWidget(self.results_loader_widget)

        # 2.5 Status Filter
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(
            ["accept", "reject", "unsure", "not_reviewed", "All"]
        )
        self.status_filter_combo.setCurrentText("accept")
        self.filter_btn = QPushButton("Filter")
        status_layout.addWidget(self.status_filter_combo)
        status_layout.addWidget(self.filter_btn)
        self.layout().addLayout(status_layout)
        self.status_filter_combo.setEnabled(False)
        self.filter_btn.setEnabled(False)

        # 3. Data Type Selection
        data_type_layout = QHBoxLayout()
        data_type_layout.addWidget(QLabel("Data Type:"))
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["Whole neuron", "CBF", "Bundles"])
        data_type_layout.addWidget(self.data_type_combo)
        self.layout().addLayout(data_type_layout)

        # 4. Hemilineage Search and Selection
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search for hemilineages...")
        self.hemilineage_list_widget = QListWidget()
        self.hemilineage_list_widget.setSelectionMode(
            QListWidget.ExtendedSelection
        )
        self.layout().addWidget(self.search_box)
        self.layout().addWidget(self.hemilineage_list_widget)

        # 5. Action Buttons
        action_layout = QHBoxLayout()
        add_btn = QPushButton("Add Layers")
        clean_btn = QPushButton("Clean All")
        plot_btn = QPushButton("Plot Tracts")
        action_layout.addWidget(add_btn)
        action_layout.addWidget(clean_btn)
        action_layout.addWidget(plot_btn)
        self.layout().addLayout(action_layout)

        # --- Connections ---
        self.connection_widget.connected.connect(
            self._on_connection_status_changed
        )
        self.results_loader_widget.results_loaded.connect(
            self._on_results_loaded
        )
        self.filter_btn.clicked.connect(self._update_hemilineage_list)
        add_btn.clicked.connect(self._on_add_layers)
        clean_btn.clicked.connect(self._on_clean_all)
        plot_btn.clicked.connect(self._on_plot_tracts)
        self.search_box.textChanged.connect(self._update_hemilineage_list)

        # --- Initial Load ---
        self.results_loader_widget.perform_initial_load()

    def _on_results_loaded(self, df, path):
        """
        Callback for when results are loaded from the file.
        """
        self.results_df = df
        print(self.results_df)
        # First, set the state of the filter controls
        if self.results_df is not None and not self.results_df.empty:
            print("Results DataFrame loaded successfully.")
            self.status_filter_combo.setEnabled(True)
            self.filter_btn.setEnabled(True)
        else:
            self.status_filter_combo.setEnabled(False)
            self.filter_btn.setEnabled(False)

        # Now, update the list based on the new state
        self._update_hemilineage_list()

    def _on_connection_status_changed(self, loader_instance):
        self.loader = loader_instance
        if self.loader:
            self._update_hemilineage_list()

    def _update_hemilineage_list(self):
        """
        Update the list of hemilineages based on search text and status filter.
        """
        self.hemilineage_list_widget.clear()
        if not self.loader:
            return

        # Determine the base list of hemilineages
        base_hemilineages = []
        filter_active = self.filter_btn.isEnabled()

        if filter_active and self.results_df is not None:
            selected_status = self.status_filter_combo.currentText()
            if selected_status == "All":
                base_hemilineages = (
                    self.results_df["Hemilineage"].unique().tolist()
                )
            else:
                base_hemilineages = (
                    self.results_df[
                        self.results_df["status"] == selected_status
                    ]["Hemilineage"]
                    .unique()
                    .tolist()
                )
        else:
            base_hemilineages = self.loader.get_hemilineage_list()

        # Filter by search text
        search_text = self.search_box.text().lower()
        filtered_list = [
            name for name in base_hemilineages if search_text in name.lower()
        ]

        for name in filtered_list:
            self.hemilineage_list_widget.addItem(QListWidgetItem(name))

    def _on_add_layers(self):
        """Add selected hemilineages as new layers to the viewer."""
        if not self.loader:
            show_warning("Please connect to a dataset first.")
            return

        selected_items = self.hemilineage_list_widget.selectedItems()
        if not selected_items:
            show_warning("No hemilineages selected.")
            return

        data_type = self.data_type_combo.currentText()

        for item in selected_items:
            hemilineage_name = item.text()
            try:
                if data_type == "Whole neuron":
                    data = self.loader.get_whole_neuron_nrrd(hemilineage_name)
                elif data_type == "CBF":
                    data = self.loader.get_cellbody_fiber_nrrd(
                        hemilineage_name
                    )
                else:  # Bundles
                    data = self.loader.get_hat_bundles_nrrd(hemilineage_name)
                layer_name = f"{hemilineage_name}_{data_type}"
                layer_kwargs = {
                    "name": layer_name,
                    "axis_labels": ("x", "y", "z"),
                    "blending": "additive",
                    "contrast_limits": [0, 1],
                    "colormap": generate_random_hex_color(),
                    "scale": (0.38, 0.38, 0.38),
                    "units": ("micron", "micron", "micron"),
                    "metadata": {"hemilineage": hemilineage_name},
                }
                new_layer = self.viewer.add_image(data, **layer_kwargs)
                self.added_layers.append(new_layer)

            except (FileNotFoundError, ValueError) as e:
                show_error(f"Failed to load {hemilineage_name}: {e}")

    def _on_clean_all(self):
        """Remove all layers added by this widget."""
        for layer in self.added_layers:
            if layer in self.viewer.layers:
                self.viewer.layers.remove(layer)
        self.added_layers.clear()
        show_info("Removed all added layers.")

    def _on_plot_tracts(self):
        """Placeholder for plotting tracts."""
        if not self.added_layers:
            show_warning("No layers have been added to plot.")
            return

        dialog = QFileDialog(self, "Save Tracts Plot")
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilter(
            "Image Files (*.png);;PDF Files (*.pdf);;All Files (*)"
        )

        # Add a checkbox to the dialog
        checkbox = QCheckBox("Plot symmetrically", dialog)
        dialog.layout().addWidget(checkbox)

        if dialog.exec_():
            save_path = dialog.selectedFiles()[0]
            plot_symmetry = checkbox.isChecked()

            active_hemilineages = {}
            for layer in self.added_layers:
                if layer in self.viewer.layers:
                    active_hemilineages[layer.metadata["hemilineage"]] = (
                        layer.colormap.name
                    )

            plot_tracts(
                active_hemilineages,
                save_path,
                self.loader,
                plot_symmetry,
                progress,
            )
            show_info(f"Plotting saved to {save_path}")
