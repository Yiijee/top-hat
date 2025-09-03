from pathlib import Path
from typing import TYPE_CHECKING

from napari.utils import progress
from napari.utils.notifications import show_error, show_info, show_warning
from qtpy.QtCore import QSettings, Signal
from qtpy.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..utils.data_loaders import FAFB_loader

if TYPE_CHECKING:
    pass


class ConnectionWidget(QWidget):
    """A widget for connecting to the FAFB dataset.

    This widget provides a user interface for specifying the path to the
    FAFB dataset, connecting to it, and validating its contents. It emits a
    signal when a connection is successfully established or fails.

    Attributes:
        connected (Signal): A Qt signal that emits the `FAFB_loader` instance
            on successful connection, or `None` on failure.
    """

    connected = Signal(object)

    def __init__(self, parent=None):
        """Initializes the ConnectionWidget.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.loader = None
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        control_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Enter path to FAFB dataset...")
        browse_btn = QPushButton("Browse")
        connect_btn = QPushButton("Connect")
        control_layout.addWidget(self.path_edit)
        control_layout.addWidget(browse_btn)
        control_layout.addWidget(connect_btn)

        self.status_label = QLabel("Status: Disconnected")

        self.layout().addLayout(control_layout)
        self.layout().addWidget(self.status_label)

        browse_btn.clicked.connect(self._on_browse)
        connect_btn.clicked.connect(self._on_connect)

        self._load_settings()

    def _load_settings(self):
        """Loads the last used data path from application settings."""
        settings = QSettings("hi-hat", "hat-viewer")
        last_path = settings.value("data_path", "")
        if last_path:
            self.path_edit.setText(last_path)
            self.status_label.setText("Status: Path loaded. Click connect.")

    def _save_settings(self):
        """Saves the current data path to application settings."""
        settings = QSettings("hi-hat", "hat-viewer")
        settings.setValue("data_path", self.path_edit.text())

    def _on_connect(self):
        """Handles the 'Connect' button click.

        Attempts to create and validate a `FAFB_loader` instance with the
        provided path. Emits the `connected` signal with the loader instance
        on success or `None` on failure.
        """
        path = self.path_edit.text()
        if not path:
            show_warning("Please provide a path.")
            return

        self.status_label.setText("Status: Connecting...")
        try:
            self.loader = FAFB_loader(path)
            self.loader.validate_dataset(progress_wrapper=progress)
            show_info("Successfully connected to dataset!")
            self._save_settings()
            self.status_label.setText(
                f"Status: Connected to {Path(path).name}"
            )
            self.connected.emit(self.loader)
        except (FileNotFoundError, ValueError, NotADirectoryError) as e:
            show_error(f"Connection failed: {e}")
            self.loader = None
            self.status_label.setText("Status: Connection failed.")
            self.connected.emit(None)

    def _on_browse(self):
        """Opens a file dialog to select the data directory."""
        path = QFileDialog.getExistingDirectory(
            self, "Select FAFB Dataset Directory"
        )
        if path:
            self.path_edit.setText(path)
            self._on_connect()
