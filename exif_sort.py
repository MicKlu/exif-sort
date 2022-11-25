#!/usr/bin/python3

import copy
from datetime import datetime
import locale
import os
from pathlib import Path
from PIL import Image
import shutil
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLineEdit
from main_window import Ui_MainWindow

__version__ = "0.1.0"

class ImageOpenError(Exception):
    """Raised if image couldn't be opened"""

    def __init__(self, path):
        super().__init__(f"Couldn't open image ({path})")

class ImageFile:
    """Class for operating on image file"""

    def __init__(self, path: Path):
        self.__path = path

    def get_date_time(self) -> datetime:
        """Extracts date of image from EXIF"""

        try:
            img = Image.open(self.__path)
            self.__exif = img.getexif()
            img.close()
        except:
            raise ImageOpenError(self.__path)

        date_time_str: str = self.__exif.get(306) # 306 - DateTime

        if len(date_time_str) == 0:
            return None

        return datetime.strptime(date_time_str, "%Y:%m:%d %H:%M:%S")

    def move(self, output_path: Path):
        """Moves file to new location"""

        new_path = output_path

        i = 1
        while new_path.exists():
            filename = output_path.stem
            extention = output_path.suffix
            new_path = output_path.parent.joinpath(f"{filename}-{i}{extention}")
            i += 1

        print(f"{self.__path} -> {new_path}")

        # output_path.parent.mkdir(parents=True, exist_ok=True)
        # shutil.copy(self.__path, new_path)
        # shutil.move(self.__path, new_path)

class ImageSorter:
    """Performs images sorting operation"""

    def __init__(self, input_dir: Path):
        self.input_dir: Path = input_dir
        self.output_dir: Path = input_dir.joinpath("sort_output")
        self.recursive: bool = False
        self.group_format: str = "%Y/%B/%d"
        self.sort_unknown: bool = False
        self.rename_format: str = None

    def sort(self):
        """Starts sorting loop"""

        for file in self.input_dir.iterdir():
            if file.is_dir():
                if self.recursive:
                    # If recursive, create new recursive sorter and perform sorting on directory
                    img_sorter = copy.copy(self)
                    img_sorter.input_dir = file
                    img_sorter.sort()
                else:
                    continue

            self.move(file)

    def move(self, path: Path):
        """Determines new image path and moves the file"""

        img = ImageFile(path)

        try:
            date_time = img.get_date_time()
        except:
            date_time = None

        filename = path.name

        output_path = self.output_dir
        if date_time is not None:
            output_path = output_path.joinpath(date_time.strftime(self.group_format))
            if self.rename_format is not None:
                filename = date_time.strftime(self.rename_format) + path.suffix
        elif date_time is None and not self.sort_unknown:
            return

        output_path = output_path.joinpath(filename)

        img.move(output_path)

class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

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

    def __on_input_directory_button_click(self):
        """Called when input's "Browse" button has been clicked"""

        self.__browse_in_out_directory(self.inputDirectoryPathEdit)

    def __on_output_directory_button_click(self):
        """Called when output's "Browse" button has been clicked"""

        self.__browse_in_out_directory(self.outputDirectoryPathEdit)

    def __browse_in_out_directory(self, pathEdit: QLineEdit):
        """Updates path field"""

        path = QFileDialog.getExistingDirectory(self, directory=pathEdit.text())

        if len(path) == 0:
            return

        pathEdit.setText(path)

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

if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())

    # # Initiate Image Sorter
    # img_sorter = ImageSorter(Path(sys.argv[1]))
    # # img_sorter.output_dir = output_dir
    # # img_sorter.recursive = True
    # # img_sorter.group_format = group_format
    # # img_sorter.sort_unknown = True
    # # img_sorter.rename_format = "%Y-%m-%d %H-%M-%S"

    # img_sorter.sort()