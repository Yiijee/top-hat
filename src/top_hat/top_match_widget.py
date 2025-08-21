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
            self.results_loader_widget.set_loader
        )
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
        self.results_loader_widget.results_loaded.connect(
            self.matching_hat_widget._on_results_loaded
        )
        self.viewer.layers.events.inserted.connect(
            self._on_new_query_image
        )  # Add this line

        # --- Perform Initial Load ---
        # This must be done after all connections are established
        self.results_loader_widget.perform_initial_load()

    def _on_new_query_image(self, event):
        """
        A new layer has been inserted. If it's a new 'query_image',
        reset the application state.
        """
        layer = event.value
        if layer.name == "query_image [1]":
            # Remove all layers except the new query_image
            for lyr in list(self.viewer.layers):
                if lyr.name != "query_image [1]":
                    self.viewer.layers.remove(lyr)
            # rename the new layer
            layer.name = "query_image"

            # Reset the widgets
            self.threshold_widget.reset()
            self.soma_detection_widget.reset()
            self.matching_hat_widget.reset()
            self.results_loader_widget.reset()
