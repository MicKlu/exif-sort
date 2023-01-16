import importlib
from pathlib import Path
import unittest
from unittest.mock import Mock, patch, PropertyMock
import sys
from threading import Thread
from typing import Union

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QFileDialog

from exif_sort.main import MainWindow, ImageSorter, SorterThread
from exif_sort.sorter import ImageSorter, ImageMoveError

main_module = importlib.import_module(".main", "exif_sort")

app = QApplication(sys.argv)


@patch.object(main_module, "SorterThread", Mock())
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
            self.assertEqual(
                mock_sorter_instance.group_format,
                self.window.outputFormatComboBox.currentText(),
            )

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
            self.assertEqual(
                mock_sorter_instance.rename_format,
                self.window.renameFormatComboBox.currentText(),
            )

        self.window.renameFormatComboBox.setCurrentText("  %d/%m.%Y at %H_%M ")
        self.click_sort()
        self.assertEqual(mock_sorter_instance.rename_format, "%d/%m.%Y at %H_%M")


@patch.object(main_module.SorterThread, "start", Mock())
@patch.object(main_module, "ImageSorter")
class UISorterInteractionCase(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow()
        self.window.inputDirectoryPathEdit.setText("/home/user/images")

    def click_sort(self):
        QTest.mouseClick(self.window.sortButton, Qt.MouseButton.LeftButton)

    def click_cancel(self):
        QTest.mouseClick(self.window.cancelButton, Qt.MouseButton.LeftButton)

    def test_hide_show_buttons(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter.return_value = mock_sorter_instance

        self.assertTrue(self.window.sortButton.isVisibleTo(self.window))
        self.assertFalse(self.window.cancelButton.isVisibleTo(self.window))

        self.click_sort()

        self.assertFalse(self.window.sortButton.isVisibleTo(self.window))
        self.assertTrue(self.window.cancelButton.isVisibleTo(self.window))

        mock_sorter_instance.on_finish()

        self.assertTrue(self.window.sortButton.isVisibleTo(self.window))
        self.assertFalse(self.window.cancelButton.isVisibleTo(self.window))

    def test_disable_enable_ui(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter.return_value = mock_sorter_instance

        always_en_dis_widgets = [
            self.window.inputDirectoryPathEdit,
            self.window.inputDirectoryBrowseButton,
            self.window.outputDirectoryPathEdit,
            self.window.outputDirectoryBrowseButton,
            self.window.recursiveCheckBox,
            self.window.skipUnknownCheckBox,
            self.window.outputFormatComboBox,
            self.window.renameCheckBox,
        ]

        # Rename not checked case
        for w in always_en_dis_widgets:
            self.assertTrue(w.isEnabled())

        self.assertFalse(self.window.renameFormatComboBox.isEnabled())

        self.click_sort()

        for w in always_en_dis_widgets:
            self.assertFalse(w.isEnabled())

        self.assertFalse(self.window.renameFormatComboBox.isEnabled())

        mock_sorter_instance.on_finish()

        for w in always_en_dis_widgets:
            self.assertTrue(w.isEnabled())

        self.assertFalse(self.window.renameFormatComboBox.isEnabled())

        # Rename checked case
        QTest.mouseClick(self.window.renameCheckBox, Qt.MouseButton.LeftButton)

        self.assertTrue(self.window.renameFormatComboBox.isEnabled())

        self.click_sort()

        self.assertFalse(self.window.renameFormatComboBox.isEnabled())

        mock_sorter_instance.on_finish()

        self.assertTrue(self.window.renameFormatComboBox.isEnabled())

    def test_cancel_button(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter.return_value = mock_sorter_instance

        self.assertTrue(self.window.sortButton.isVisibleTo(self.window))

        self.click_sort()

        self.assertTrue(self.window.cancelButton.isVisibleTo(self.window))

        self.click_cancel()

        self.assertFalse(self.window.cancelButton.isEnabled())
        mock_sorter_instance.cancel.assert_called()

        mock_sorter_instance.on_finish()

        self.assertTrue(self.window.cancelButton.isEnabled())

    def test_progress(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter.return_value = mock_sorter_instance

        self.click_sort()

        mock_sorter_instance.on_move(Path(), Path(), 0.25)

        self.assertEqual(self.window.statusProgress.value(), 25)

        mock_sorter_instance.on_skip(Path(), 0.50999999)

        self.assertEqual(self.window.statusProgress.value(), 50)

        mock_sorter_instance.on_error(RuntimeError(""), 1.0)

        self.assertEqual(self.window.statusProgress.value(), 100)


@patch.object(
    main_module.SorterThread, "start", lambda self: self._SorterThread__sorter.sort()
)
class ImageSorterStatusCase(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow()
        self.window.inputDirectoryPathEdit.setText("/home/user/images")

    def click_sort(self):
        QTest.mouseClick(self.window.sortButton, Qt.MouseButton.LeftButton)

    def click_cancel(self):
        QTest.mouseClick(self.window.cancelButton, Qt.MouseButton.LeftButton)

    @patch.object(main_module, "ImageSorter")
    def test_on_move(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter.return_value = mock_sorter_instance

        self.click_sort()

        mock_sorter_instance.on_move(
            Path("/home/user/images/image1.png"), Path.home() / Path("image1.png"), 1
        )

        items_count = self.window.statusList.count()
        msg = self.window.statusList.item(items_count - 1).text()

        self.assertRegex(msg, "Moved")

    @patch.object(main_module, "ImageSorter")
    def test_on_skip(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter.return_value = mock_sorter_instance

        self.click_sort()

        mock_sorter_instance.on_skip(Path("/home/user/images/image1.png"), 1)

        items_count = self.window.statusList.count()
        msg = self.window.statusList.item(items_count - 1).text()

        self.assertRegex(msg, "Skipped")

    def test_on_error(self):
        with patch.object(Path, "iterdir") as mock_iterdir:
            mock_iterdir.side_effect = [
                PermissionError,
                FileNotFoundError,
                OSError,
            ]
            expected_msg = ["Permission denied", "not found", "Error"]

            for em in expected_msg:
                self.click_sort()

                items_count = self.window.statusList.count()
                msg = self.window.statusList.item(items_count - 2).text()

                self.assertRegex(msg, em)

        with patch.object(Path, "iterdir") as mock_iterdir:
            mock_iterdir.return_value = [Path("/home/user/images/image1.png")]
            with patch.object(Path, "is_dir") as mock_is_dir:
                mock_is_dir.return_value = False
                with patch.object(
                    main_module.ImageSorter, "_ImageSorter__move"
                ) as mock___move:
                    mock___move.side_effect = [
                        ImageMoveError(
                            "/home/user/images/image1.png", PermissionError()
                        ),
                        ImageMoveError(
                            "/home/user/images/image1.png", FileNotFoundError()
                        ),
                        ImageMoveError("/home/user/images/image1.png", OSError()),
                    ]

                    expected_msg = ["Permission denied", "not found", "Error"]

                    for em in expected_msg:
                        self.click_sort()

                        items_count = self.window.statusList.count()
                        msg = self.window.statusList.item(items_count - 2).text()

                        self.assertRegex(msg, em)

    @patch.object(main_module, "ImageSorter")
    def test_on_error_no_events(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter.return_value = mock_sorter_instance

        self.click_sort()

        mock_sorter_instance.on_error(
            RuntimeError(
                "empty-queue",
                "No event received in last 60 seconds.",
            ),
            0.66,
        )

        items_count = self.window.statusList.count()
        msg = self.window.statusList.item(items_count - 1).text()

        self.assertRegex(msg, "Nothing")

    @patch.object(main_module, "ImageSorter")
    def test_on_finish(self, mock_sorter: Union["ImageSorter", Mock]):
        mock_sorter_instance = Mock()
        mock_sorter.return_value = mock_sorter_instance

        self.click_sort()

        mock_sorter_instance.on_move(
            Path("/home/user/images/image1.png"), Path.home() / Path("image1.png"), 1
        )
        mock_sorter_instance.on_finish()

        items_count = self.window.statusList.count()
        msg = self.window.statusList.item(items_count - 1).text()

        self.assertRegex(msg, "Ready")

        self.click_sort()
        mock_sorter_instance.on_move(
            Path("/home/user/images/image1.png"), Path.home() / Path("image1.png"), 1
        )
        self.click_cancel()
        mock_sorter_instance.on_finish()

        items_count = self.window.statusList.count()
        msg = self.window.statusList.item(items_count - 2).text()

        self.assertRegex(msg, "cancel")


@patch.object(QFileDialog, "getExistingDirectory")
class BrowseCase(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow()
        self.window.inputDirectoryPathEdit.setText("/home/user/images")
        self.window.outputDirectoryPathEdit.setText("/home/user/images")

    def test_browse_input(self, mock_getExistingDirectory: Mock):
        mock_getExistingDirectory.side_effect = ["", "/home/user/pictures/"]

        input_widget = self.window.inputDirectoryPathEdit

        self.assertEqual(input_widget.text(), "/home/user/images")

        QTest.mouseClick(
            self.window.inputDirectoryBrowseButton, Qt.MouseButton.LeftButton
        )

        self.assertEqual(input_widget.text(), "/home/user/images")

        QTest.mouseClick(
            self.window.inputDirectoryBrowseButton, Qt.MouseButton.LeftButton
        )

        self.assertEqual(input_widget.text(), "/home/user/pictures/")

    def test_browse_output(self, mock_getExistingDirectory: Mock):
        mock_getExistingDirectory.side_effect = ["", "/home/user/pictures/"]

        output_widget = self.window.outputDirectoryPathEdit

        self.assertEqual(output_widget.text(), "/home/user/images")

        QTest.mouseClick(
            self.window.outputDirectoryBrowseButton, Qt.MouseButton.LeftButton
        )

        self.assertEqual(output_widget.text(), "/home/user/images")

        QTest.mouseClick(
            self.window.outputDirectoryBrowseButton, Qt.MouseButton.LeftButton
        )

        self.assertEqual(output_widget.text(), "/home/user/pictures/")
