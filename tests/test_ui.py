import importlib
from pathlib import Path
import unittest
from unittest.mock import Mock, patch, PropertyMock
import sys
from typing import Union

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from exif_sort.main import MainWindow, ImageSorter
from exif_sort.sorter import ImageSorter

main_module = importlib.import_module(".main", "exif_sort")

app = QApplication(sys.argv)

@patch.object(main_module, "ImageSorter")
class ImageSorterInitCase(unittest.TestCase):

    def setUp(self):
        self.window = MainWindow()
        self.window.inputDirectoryPathEdit.setText("/home/user/images")

    def click_sort(self):
        QTest.mouseClick(self.window.sortButton, Qt.MouseButton.LeftButton)

    def test_input_path(self, mock_sorter: Union["ImageSorter", Mock]):
        self.window.inputDirectoryPathEdit.setText("")
        status_msg_count_before = self.window.statusList.count()
        self.click_sort()
        status_msg_count_after = self.window.statusList.count()

        mock_sorter.assert_not_called()
        self.assertGreater(status_msg_count_after, status_msg_count_before)

        path = Path("/home/user/images")
        self.window.inputDirectoryPathEdit.setText(str(path))
        self.click_sort()
        mock_sorter.assert_called_once_with(path)

    def test_output_path(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter_instance.output_dir = Mock()
        mock_sorter.return_value = mock_sorter_instance
        
        self.window.outputDirectoryPathEdit.setText("")
        self.click_sort()

        output_dir = mock_sorter_instance.output_dir
        self.assertEqual(output_dir, Path.home())
        self.assertTrue(output_dir.exists())

        path = Path("/home/user/images/sorted")
        self.window.outputDirectoryPathEdit.setText(str(path))
        self.click_sort()

        output_dir = mock_sorter_instance.output_dir
        self.assertEqual(output_dir, path)

    def test_recursive(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter_instance.recursive = Mock()
        mock_sorter.return_value = mock_sorter_instance

        self.window.recursiveCheckBox.setChecked(False)
        self.click_sort()

        self.assertFalse(mock_sorter_instance.recursive)

        self.window.recursiveCheckBox.setChecked(True)
        self.click_sort()

        self.assertTrue(mock_sorter_instance.recursive)

    def test_group_format(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter_instance.group_format = Mock()
        mock_sorter.return_value = mock_sorter_instance

        for i in range(self.window.outputFormatComboBox.count()):        
            self.window.outputFormatComboBox.setCurrentIndex(i)
            self.click_sort()
            self.assertEqual(mock_sorter_instance.group_format, self.window.outputFormatComboBox.currentText())

        self.window.outputFormatComboBox.setCurrentText("  %d/%m.%Y at %H_%M ")
        self.click_sort()
        self.assertEqual(mock_sorter_instance.group_format, "%d/%m.%Y at %H_%M")

    def test_sort_unknown(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter_instance.sort_unknown = Mock()
        mock_sorter.return_value = mock_sorter_instance

        self.window.skipUnknownCheckBox.setChecked(False)
        self.click_sort()

        self.assertTrue(mock_sorter_instance.sort_unknown)

        self.window.skipUnknownCheckBox.setChecked(True)
        self.click_sort()

        self.assertFalse(mock_sorter_instance.sort_unknown)

    def test_rename_format(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter_instance.rename_format = None
        mock_sorter.return_value = mock_sorter_instance

        self.window.renameCheckBox.setChecked(False)
        self.window.renameFormatComboBox.setCurrentIndex(0)
        self.click_sort()
        self.assertIsNone(mock_sorter_instance.rename_format)

        self.window.renameCheckBox.setChecked(True)

        for i in range(self.window.renameFormatComboBox.count()):        
            self.window.renameFormatComboBox.setCurrentIndex(i)
            self.click_sort()
            self.assertEqual(mock_sorter_instance.rename_format, self.window.renameFormatComboBox.currentText())

        self.window.renameFormatComboBox.setCurrentText("  %d/%m.%Y at %H_%M ")
        self.click_sort()
        self.assertEqual(mock_sorter_instance.rename_format, "%d/%m.%Y at %H_%M")