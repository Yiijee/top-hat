from typing import TYPE_CHECKING

from napari.utils import progress
from napari.utils.notifications import show_error, show_info, show_warning
from qtpy.QtCore import QSettings, Signal
from qtpy.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from ..utils.data_loaders import FAFB_loader

if TYPE_CHECKING:
    pass


class ConnectionWidget(QWidget):
    """A widget to handle FAFB dataset connection."""

    connected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.loader = None
        self.setLayout(QHBoxLayout())
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Enter path to FAFB dataset...")
        browse_btn = QPushButton("Browse")
        connect_btn = QPushButton("Connect")
        self.layout().addWidget(self.path_edit)
        self.layout().addWidget(browse_btn)
        self.layout().addWidget(connect_btn)

        browse_btn.clicked.connect(self._on_browse)
        connect_btn.clicked.connect(self._on_connect)

        self._load_settings()

    def _load_settings(self):
        """Load the last used data path from settings."""
        settings = QSettings("top-hat", "hat-viewer")
        last_path = settings.value("data_path", "")
        if last_path:
            self.path_edit.setText(last_path)

    def _save_settings(self):
        """Save the current data path to settings."""
        settings = QSettings("top-hat", "hat-viewer")
        settings.setValue("data_path", self.path_edit.text())

    def _on_connect(self):
        """Connect to the FAFB dataset path."""
        path = self.path_edit.text()
        if not path:
            show_warning("Please provide a path.")
            return

        try:
            self.loader = FAFB_loader(path)
            self.loader.validate_dataset(progress_wrapper=progress)
            show_info("Successfully connected to dataset!")
            self._save_settings()
            self.connected.emit(self.loader)
        except (FileNotFoundError, ValueError, NotADirectoryError) as e:
            show_error(f"Connection failed: {e}")
            self.loader = None
            self.connected.emit(None)

    def _on_browse(self):
        """Open a dialog to select the data directory."""
        path = QFileDialog.getExistingDirectory(
            self, "Select FAFB Dataset Directory"
        )
        if path:
            self.path_edit.setText(path)
            self._on_connect()
