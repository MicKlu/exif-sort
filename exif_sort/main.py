from datetime import datetime
import locale
from pathlib import Path
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLineEdit
from exif_sort.ui.main_window import Ui_MainWindow

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

        # Quit application
        self.actionQuit.triggered.connect(self.__quit)

    def __log_status(self, msg: str):
        self.statusList.addItem(msg)

    def __on_input_directory_button_click(self):
        """Called when input's "Browse" button has been clicked"""

        self.__browse_in_out_directory(self.inputDirectoryPathEdit)

    def __on_output_directory_button_click(self):
        """Called when output's "Browse" button has been clicked"""

        self.__browse_in_out_directory(self.outputDirectoryPathEdit)

    def __browse_in_out_directory(self, path_edit: QLineEdit):
        """Updates path field"""

        path = QFileDialog.getExistingDirectory(self, directory=path_edit.text())

        if len(path) == 0:
            return

        path_edit.setText(path)

    def __on_output_directory_path_change(self, text: str):
        """Called when output path has been changed"""

        self.__update_output_preview()

    def __on_output_format_change(self, text: str):
        """Called when output format has been changed"""

        self.__update_output_preview()

    def __on_rename_format_change(self, text: str):
        """Called when rename format has been changed"""

        self.__update_output_preview()

    def __on_rename_click(self, checked: bool):
        """Called when renaming files has been toggled"""

        self.__update_output_preview()

    def __update_output_preview(self):
        """Updates output preview"""

        date = datetime.now()

        # Get output path
        path = self.outputDirectoryPathEdit.text().strip()
        if len(path) > 0:
            output_path = Path(path)
        else:
            output_path = Path.home()

        # Add options format
        sort_format = self.outputFormatComboBox.currentText()
        output_path = output_path.joinpath(date.strftime(sort_format))

        # Add rename format
        if self.renameCheckBox.isChecked():
            rename_format = self.renameFormatComboBox.currentText()
            output_path = output_path.joinpath(date.strftime(rename_format))
        else:
            output_path = output_path.joinpath("image")

        self.outputPreviewValueLabel.setText(str(output_path) + ".jpg")

    def __quit(self):
        self.close()

def main():
    locale.setlocale(locale.LC_ALL, "")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    return app.exec()
