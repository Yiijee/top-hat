from typing import TYPE_CHECKING

from qtpy.QtWidgets import QVBoxLayout, QWidget

from .widgets import (
    ConnectionWidget,
    MatchingHatWidget,
    ResultsLoaderWidget,
    SomaDetectionWidget,
    ThresholdWidget,
)

if TYPE_CHECKING:
    import napari


class TopMatch(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer
        self.setLayout(QVBoxLayout())

        # 1. Data Connection Widget
        self.connection_widget = ConnectionWidget()
        self.layout().addWidget(self.connection_widget)

        # 2. Results Loader
        self.results_loader_widget = ResultsLoaderWidget(self.viewer)
        self.layout().addWidget(self.results_loader_widget)

        # 3. Threshold Widget
        self.threshold_widget = ThresholdWidget(self.viewer)
        self.layout().addWidget(self.threshold_widget)

        # 4. Soma Detection Widget
        self.soma_detection_widget = SomaDetectionWidget(self.viewer)
        self.layout().addWidget(self.soma_detection_widget)

        # 5. Matching Hat Widget
        self.matching_hat_widget = MatchingHatWidget(
            self.viewer, self.soma_detection_widget
        )
        self.layout().addWidget(self.matching_hat_widget)

        # --- Connections ---
        self.connection_widget.connected.connect(
            self.soma_detection_widget.set_loader
        )
        self.connection_widget.connected.connect(
            self.matching_hat_widget.set_loader
        )
        self.soma_detection_widget.matched.connect(
            self.matching_hat_widget.set_hemilineages
        )
        self.results_loader_widget.results_loaded.connect(
            self.soma_detection_widget._on_results_loaded
        )
        self.results_loader_widget.results_loaded.connect(
            self.matching_hat_widget._on_results_loaded
        )
