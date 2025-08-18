from typing import TYPE_CHECKING

from qtpy.QtWidgets import QVBoxLayout, QWidget

from .utils.qwidget_modules import (
    ConnectionWidget,
    MatchingHatWidget,
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

        # 2. Threshold Widget
        self.threshold_widget = ThresholdWidget(self.viewer)
        self.layout().addWidget(self.threshold_widget)

        # 3. Soma Detection Widget
        self.soma_detection_widget = SomaDetectionWidget(self.viewer)
        self.layout().addWidget(self.soma_detection_widget)

        # 4. Matching Hat Widget
        self.matching_hat_widget = MatchingHatWidget(self.viewer)
        self.layout().addWidget(self.matching_hat_widget)

        # Connect the connection widget to the other widgets
        self.connection_widget.connected.connect(
            self.soma_detection_widget.set_loader
        )
        self.connection_widget.connected.connect(
            self.matching_hat_widget.set_loader
        )
        self.soma_detection_widget.matched.connect(
            self.matching_hat_widget.set_hemilineages
        )

        # Placeholder for other functionalities
        # self.combo_btn = QPushButton("Crazy Thursday V me fifty!!")
        # self.combo_btn.clicked.connect(self.Your_Combo)
        # self.layout().addWidget(self.combo_btn)

    # def Your_Combo(self):
    #     # Add your combo functionality here
    #     pass
