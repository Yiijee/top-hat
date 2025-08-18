from typing import TYPE_CHECKING

from qtpy.QtWidgets import (
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .core.cellbody_matching import centroid_matching
from .utils.qwidget_modules import ConnectionWidget

if TYPE_CHECKING:
    import napari


class TopMatch(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer
        self.loader = None
        # --- UI Setup ---
        self.setLayout(QVBoxLayout())

        # 1. Data Connection
        self.connection_widget = ConnectionWidget()
        self.layout().addWidget(self.connection_widget)
        self.connection_widget.connected.connect(
            self._on_connection_status_changed
        )

        # 2. Detect connection
        self.info_label = QLabel(
            "Select points in the viewer to record (z, y, x) coordinates."
        )
        self.layout().addWidget(self.info_label)

        self.points_layer = viewer.add_points(name="Selected Points", ndim=3)
        self.points_layer.events.data.connect(self.on_points_added)

        # Add button to get cluster centroid
        self.centroid_btn = QPushButton("Get Cluster Centroid")
        self.centroid_btn.clicked.connect(self.get_cluster_centroid)
        self.layout().addWidget(self.centroid_btn)

        # Add button for Later functions
        self.combo_btn = QPushButton("Crazy Thursday V me fifty!!")
        self.combo_btn.clicked.connect(self.Your_Combo)
        self.layout().addWidget(self.combo_btn)

        # Store last calculated centroid
        self.last_centroid = None
        self.last_matched_hemilineages = None

    def _on_connection_status_changed(self, loader_instance):
        self.loader = loader_instance

    def on_points_added(self, event):
        coords = self.points_layer.data
        labels = [str(i + 1) for i in range(len(coords))]
        self.points_layer.text = {"string": labels, "size": 8, "color": "red"}

    def calculate_centroid(self, indices):
        """Return the centroid coordinates for selected indices."""
        coords = self.points_layer.data
        if len(coords) == 0 or not indices:
            return None
        selected_coords = coords[indices]
        centroid = selected_coords.mean(axis=0)
        return tuple(float(c) for c in centroid)

    def get_cluster_centroid(self):
        coords = self.points_layer.data
        if len(coords) == 0:
            self.info_label.setText("No points selected.")
            return None

        indices_str, ok = QInputDialog.getText(
            self,
            "Input Point Indices",
            "Enter point indices (e.g., 1,2,3 or 1-5) used for calculating the cell cluster centroid:",
        )
        if not ok or not indices_str.strip():
            return None

        try:
            indices = []
            for part in indices_str.split(","):
                part = part.strip()
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    indices.extend(range(start - 1, end))
                elif part:
                    indices.append(int(part) - 1)
            centroid_tuple = self.calculate_centroid(indices)
            if centroid_tuple is None:
                self.info_label.setText("No valid points for centroid.")
                return None
            self.last_centroid = centroid_tuple

            if "LM_centroid" in self.viewer.layers:
                self.viewer.layers["LM_centroid"].data = [centroid_tuple]
            else:
                self.viewer.add_points(
                    [centroid_tuple],
                    name="LM_centroid",
                    size=15,
                    face_color="yellow",
                )

            user_centroid = centroid_tuple[::-1]
            result = centroid_matching(user_centroid, self.loader)
            self.last_matched_hemilineages = result
            print(f"Matched hemilineages: {result['hemilineages']}")
            return centroid_tuple
        except (OSError, ValueError, KeyError) as e:
            self.info_label.setText(f"Error: {e}")
            return None

    def Your_Combo(self):
        """Write matched hemilineages info to Enjoy_the_Combo.txt"""
        if self.last_matched_hemilineages is None:
            self.info_label.setText("No matched hemilineages data to save.")
            return
        try:
            with open("Enjoy_the_Combo.txt", "w") as f:
                f.write(str(self.last_matched_hemilineages))
            self.info_label.setText(
                "Enjoy the Combo!check a file called Enjoy_the_Combo.txt"
            )
        except (OSError, ValueError) as e:
            self.info_label.setText(f"Error saving combo: {e}")
