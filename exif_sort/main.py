from datetime import datetime
import locale
from pathlib import Path
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLineEdit
from exif_sort.ui.main_window import Ui_MainWindow

from exif_sort.sorter import ImageSorter

class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.__log_status("Ready")

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)

        # Hide unusable widgets on init
        self.cancelButton.setVisible(False)

        # Open FileDialogs and update path fields
        self.inputDirectoryBrowseButton.clicked.connect(self.__on_input_directory_button_click)
        self.outputDirectoryBrowseButton.clicked.connect(self.__on_output_directory_button_click)

        # Update output preview on each path's part change
        self.outputDirectoryPathEdit.textChanged.connect(self.__on_output_directory_path_change)
        self.outputFormatComboBox.currentTextChanged.connect(self.__on_output_format_change)
        self.renameFormatComboBox.currentTextChanged.connect(self.__on_rename_format_change)
        self.renameCheckBox.clicked.connect(self.__on_rename_click)

        # Start/cancel sorting
        self.sortButton.clicked.connect(self.__on_sort_button_click)
        self.cancelButton.clicked.connect(self.__on_cancel_button_click)

        # Quit application
        self.actionQuit.triggered.connect(self.__quit)

    def __log_status(self, msg: str):
        """Displays message in status listbox"""
        self.statusList.addItem(msg)
        self.statusList.scrollToBottom()

    def __on_input_directory_button_click(self):
        """Called when input's "Browse" button has been clicked."""
        self.__browse_in_out_directory(self.inputDirectoryPathEdit)

    def __on_output_directory_button_click(self):
        """Called when output's "Browse" button has been clicked."""
        self.__browse_in_out_directory(self.outputDirectoryPathEdit)

    def __browse_in_out_directory(self, path_edit: QLineEdit):
        """Updates path field."""
        path = QFileDialog.getExistingDirectory(self, directory=path_edit.text())

        if len(path) == 0:
            return

        path_edit.setText(path)

    def __on_output_directory_path_change(self, text: str):
        """Called when output path has been changed."""
        self.__update_output_preview()

    def __on_output_format_change(self, text: str):
        """Called when output format has been changed."""
        self.__update_output_preview()

    def __on_rename_format_change(self, text: str):
        """Called when rename format has been changed."""
        self.__update_output_preview()

    def __on_rename_click(self, checked: bool):
        """Called when renaming files has been toggled."""
        self.__update_output_preview()

    def __update_output_preview(self):
        """Updates output preview."""
        date = datetime.now()

        # Get output path
        path = self.outputDirectoryPathEdit.text().strip()
        if len(path) > 0:
            output_path = Path(path)
        else:
            output_path = Path.home()

        # Add options format
        sort_format = self.outputFormatComboBox.currentText().strip()
        output_path = output_path.joinpath(date.strftime(sort_format))

        # Add rename format
        if self.renameCheckBox.isChecked():
            rename_format = self.renameFormatComboBox.currentText().strip()
            output_path = output_path.joinpath(date.strftime(rename_format))
        else:
            output_path = output_path.joinpath("image")

        self.outputPreviewValueLabel.setText(str(output_path) + ".jpg")

    def __on_sort_button_click(self):
        """Called when "Sort" button has been clicked."""
        # Get input path
        input_path = self.inputDirectoryPathEdit.text().strip()
        if len(input_path) == 0:
            self.__log_status("Invalid input directory")
            return

        input_path = Path(input_path)

        # Get output path
        output_path = self.outputDirectoryPathEdit.text().strip()

        if len(output_path) > 0:
            output_path = Path(output_path)
        else:
            output_path = Path.home()

        # Initialize sorter
        sorter = ImageSorter(input_path)
        sorter.output_dir = output_path
        sorter.recursive = self.recursiveCheckBox.isChecked()
        sorter.group_format = self.outputFormatComboBox.currentText().strip()
        sorter.sort_unknown = not self.skipUnknownCheckBox.isChecked()

        if self.renameCheckBox.isChecked():
            sorter.rename_format = self.renameFormatComboBox.currentText().strip()

        sorter.on_finish = self.__on_sort_finish
        sorter.on_move = self.__on_sort_move
        sorter.on_skip = self.__on_sort_skip
        sorter.on_error = self.__on_sort_error

        # Toggle Cancel button
        self.sortButton.setVisible(False)
        self.cancelButton.setVisible(True)

        # Start sorting
        sorter.sort()

    def __on_sort_finish(self):
        """Called once sorting finishes."""
        # Toggle Sort button
        self.sortButton.setVisible(True)
        self.cancelButton.setVisible(False)

    def __on_sort_move(self, old_path: str, new_path: str):
        """Called when file has been moved."""
        self.__log_status(f"Moved \"{old_path}\" to \"{new_path}\"")

    def __on_sort_skip(self, path: str):
        """Called when file has been skipped."""
        self.__log_status(f"Skipped \"{path}\"")

    def __on_sort_error(self, exception: Exception):
        msg = "Error: "
        if isinstance(exception, PermissionError):
            msg += f"Permission denied to {exception.filename}"
        elif isinstance(exception, FileNotFoundError):
            msg += f"{exception.filename} not found"

        self.__log_status(msg)

    def __on_cancel_button_click(self):
        """Called when "Cancel" button has been clicked."""
        pass

    def __quit(self):
        """Closes window and exits application."""
        self.close()

def main():
    locale.setlocale(locale.LC_ALL, "")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    return app.exec()
