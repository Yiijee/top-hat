from typing import TYPE_CHECKING

from napari.utils.notifications import show_error, show_info, show_warning
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    import napari


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

    def reset(self):
        """Reset the widget for a new query image."""
        if "binarized_image" in self.viewer.layers:
            self.viewer.layers.remove("binarized_image")

        # Disconnect signals to avoid issues on reset
        try:
            self.threshold_slider.valueChanged.disconnect()
            self.threshold_box.textChanged.disconnect()
        except (TypeError, RuntimeError):
            # In case they were never connected or already disconnected
            pass

        self.threshold_box.clear()
        self.threshold_slider.setValue(0)
        self.threshold_box.setEnabled(False)
        self.threshold_slider.setEnabled(False)
        self.is_initialized = False

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
                lambda t: self.threshold_slider.setValue(int(float(t.strip())))
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
