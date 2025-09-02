from typing import TYPE_CHECKING

from napari.utils.notifications import show_error, show_info, show_warning
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.cellbody_matching import _JRC2018U_mirror, centroid_matching

if TYPE_CHECKING:
    import napari


class SomaDetectionWidget(QWidget):
    """A widget for soma detection and centroid calculation.

    This widget allows users to select points in the napari viewer, calculate
    their centroid, and then use that centroid to find matching hemilineages
    based on soma proximity.

    Attributes:
        matched (Signal): A Qt signal that emits a list of matched hemilineage
            names.
        viewer (napari.viewer.Viewer): The napari viewer instance.
        loader (FAFB_loader): An instance of the data loader.
        results_df (pd.DataFrame): A DataFrame holding the matching results.
        manual_centroid (tuple): The (z, y, x) coordinates of the last
            calculated centroid.
        last_matched_hemilineages (list[str]): A list of hemilineages from the
            most recent soma matching operation.
    """

    matched = Signal(list)

    def __init__(self, viewer: "napari.viewer.Viewer", parent=None):
        """Initializes the SomaDetectionWidget.

        Args:
            viewer (napari.viewer.Viewer): The napari viewer instance.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.viewer = viewer
        self.loader = None
        self.results_df = None
        self.manual_centroid = None
        self.last_matched_hemilineages = None

        self.setLayout(QVBoxLayout())

        # --- UI Setup ---
        self.info_label = QLabel(
            "Select points in the viewer to record (z, y, x) coordinates."
        )
        # initiate LM centroids layer
        self.viewer.add_points(
            name="LM_centroid", size=15, face_color="red", ndim=3
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

        self.viewer.layers.events.inserted.connect(self._on_layers_changed)
        self.viewer.layers.events.removed.connect(self._on_layers_changed)
        self._update_enabled_state()

    def reset(self):
        """Resets the widget to its initial state for a new query."""
        if "Selected Points" in self.viewer.layers:
            self.viewer.layers["Selected Points"].data = []
        if "LM_centroid" in self.viewer.layers:
            self.viewer.layers["LM_centroid"].data = []
        if "Selected Points" not in self.viewer.layers:
            self.points_layer = self.viewer.add_points(
                name="Selected Points", ndim=3
            )
        if "LM_centroid" not in self.viewer.layers:
            self.viewer.add_points(
                name="LM_centroid", size=15, face_color="red", ndim=3
            )
        self.manual_centroid = None
        self.last_matched_hemilineages = None
        self.info_label.setText(
            "Select points in the viewer to record (z, y, x) coordinates."
        )

    def _update_enabled_state(self):
        """Enables or disables widget controls based on the current state."""
        binarized_image_exists = "binarized_image" in self.viewer.layers
        enabled = all(
            [
                self.loader is not None,
                self.results_df is not None,
                binarized_image_exists,
            ]
        )
        self.centroid_btn.setEnabled(enabled)
        if not enabled:
            self.info_label.setText(
                "Connect to data, load results, and create a binarized image to enable."
            )
        else:
            self.info_label.setText(
                "Select points in the viewer to record (z, y, x) coordinates."
            )

    def _on_layers_changed(self):
        """Responds to changes in napari viewer layers."""
        self._update_enabled_state()

    def _on_results_loaded(self, df, path):
        """Handles loaded results, adding centroids to the viewer.

        Args:
            df (pd.DataFrame): The DataFrame containing the results.
            path (str): The path to the file from which results were loaded.
        """
        print("Results loaded is triggered for soma detection")
        self.results_df = df
        self._update_enabled_state()
        if df is not None and "query_centroid" in df.columns:
            centroids = []
            for _, row in df.iterrows():
                centroid_str = row["query_centroid"]
                if isinstance(centroid_str, str):
                    try:
                        # Assuming format "(z, y, x)"
                        coords = [
                            float(c.strip())
                            for c in centroid_str.strip("()").split(",")
                        ]
                        mirror_coords = _JRC2018U_mirror(coords[::-1])[::-1]
                        centroids.extend([coords, mirror_coords])
                    except (ValueError, IndexError):
                        continue  # Skip malformed entries

            if centroids:
                if "LM_centroid" in self.viewer.layers:
                    self.viewer.layers["LM_centroid"].data = centroids
                else:
                    self.viewer.add_points(
                        centroids,
                        name="LM_centroid",
                        size=15,
                        face_color="red",
                    )

    def set_loader(self, loader_instance):
        """Sets the data loader instance.

        Args:
            loader_instance (FAFB_loader): The data loader to use.
        """
        self.loader = loader_instance
        self._update_enabled_state()

    def _on_points_added(self, event):
        """Updates point labels when data changes in the points layer.

        Args:
            event (napari.utils.events.Event): The data change event.
        """
        coords = self.points_layer.data
        labels = [str(i + 1) for i in range(len(coords))]
        self.points_layer.text = {"string": labels, "size": 7, "color": "red"}
        self.points_layer.size = 5

    def _calculate_centroid(self, indices):
        """Calculates the centroid for a given set of point indices.

        Args:
            indices (list[int]): A list of integer indices corresponding to
                the points in the 'Selected Points' layer.

        Returns:
            tuple[float, float, float] | None: The (z, y, x) coordinates of
                the centroid, or None if no valid points are found.
        """
        coords = self.points_layer.data
        if len(coords) == 0 or not indices:
            return None
        selected_coords = coords[indices]
        return tuple(float(c) for c in selected_coords.mean(axis=0))

    def _get_cluster_centroid(self):
        """Gets point indices from the user, calculates the centroid, and runs matching."""
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
            "Enter point indices (e.g., 1,2,3 or 1-5):",
            text="All",
        )
        if not ok:
            return

        try:
            indices = []
            # If user enters "All" or leaves it blank, use all points
            if not indices_str.strip() or indices_str.strip().lower() == "all":
                indices = list(range(len(self.points_layer.data)))
            else:
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

            self.manual_centroid = centroid_tuple
            self._update_viewer_with_centroid(centroid_tuple)

            # Clean up selection points
            self.points_layer.data = []

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
        """Adds or updates the centroid point layer in the viewer.

        Also adds the mirrored centroid.

        Args:
            centroid (tuple): The (z, y, x) coordinates of the centroid.
        """
        mirrored_centroid = _JRC2018U_mirror(centroid[::-1])[::-1]
        points_to_add = [centroid, mirrored_centroid]

        if "LM_centroid" in self.viewer.layers:
            self.viewer.layers["LM_centroid"].add(points_to_add)
        else:
            self.viewer.add_points(
                points_to_add,
                name="LM_centroid",
                size=15,
                face_color="yellow",
            )
