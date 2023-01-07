from datetime import datetime
import locale
from pathlib import Path
import time
from threading import Thread
import unittest
from unittest.mock import Mock, patch, create_autospec

import PIL

import exif_sort
from exif_sort.sorter import ImageSorter, ImageMoveError

class InputPath(type(Path())):
    def __init__(self, path: str, is_dir=False, *args, **kwargs):
        super().__init__()

        self.__files = []
        self.__is_dir = is_dir

    def add_file(self, filename: str) -> "InputPath":
        file = InputPath(self / Path(filename))
        self.__files.append(file)
        return file

    def add_dir(self, dirname: str) -> "InputPath":
        dir = InputPath(self / Path(dirname), is_dir=True)
        self.__files.append(dir)
        return dir

    def iterdir(self) -> list:
        return self.__files

    def is_dir(self) -> bool:
        return self.__is_dir

    def tree(self, intend=0) -> None:
        for f in self.__files:
            for i in range(0, intend):
                print("  ", end="")
            print(f)
            if f.is_dir():
                f.tree(intend + 1)

    def itertree(self):
        for f in self.__files:
            yield f
            if f.is_dir():
                for ff in f.itertree():
                    yield ff

def create_test_input_path() -> InputPath:
    ip = InputPath("/home/user/example_input_dir", is_dir=True)
    ip.add_file("image1.jpg")
    ip.add_file("image2.jpg")
    ip.add_file("image3.jpg")
    ip.add_file("image4.jpg")

    d = ip.add_dir("holidays")
    d.add_file("IMG001.jpg")
    d.add_file("IMG002.jpg")
    
    d = ip.add_dir("random stuff")
    d.add_file("DSC0001.jpg")
    d.add_file("DSC0002.jpg")
    d.add_file("DSC0003.jpg")

    d = d.add_dir("nsfw")
    d.add_file("archive.zip")
    d.add_file("password.txt")
    d.add_file("img1.jpg")

    return ip

def mock_move(self, output_path):
    return output_path

@patch.object(ImageSorter, "_ImageSorter__move")
class TestImageSorterSort(unittest.TestCase):

    def test_preparation(self, mock_sorter_move: Mock):
        ip = create_test_input_path()

        sorter = ImageSorter(ip)
        sorter.output_dir = Path("/home/user/example_output_dir")

        sorter.sort()

        self.assertEqual(len(sorter._ImageSorter__dirs), 1)
        self.assertEqual(sorter._ImageSorter__dirs[0]["dir"], ip)
        self.assertEqual(sorter._ImageSorter__dirs[0]["files"], 4)

    def test_recursive_preparation(self, mock_sorter_move: Mock):
        ip = create_test_input_path()

        sorter = ImageSorter(ip)
        sorter.output_dir = Path("/home/user/example_output_dir")
        sorter.recursive = True

        sorter.sort()

        self.assertEqual(len(sorter._ImageSorter__dirs), 4)

        dirs = [str(d["dir"]) for d in sorter._ImageSorter__dirs]

        self.assertTrue("/home/user/example_input_dir" in dirs)
        self.assertTrue("/home/user/example_input_dir/holidays" in dirs)
        self.assertTrue("/home/user/example_input_dir/random stuff" in dirs)
        self.assertTrue("/home/user/example_input_dir/random stuff/nsfw" in dirs)

        files = {str(d["dir"]): d["files"] for d in sorter._ImageSorter__dirs}

        self.assertEqual(files["/home/user/example_input_dir"], 4)
        self.assertEqual(files["/home/user/example_input_dir/holidays"], 2)
        self.assertEqual(files["/home/user/example_input_dir/random stuff"], 3)
        self.assertEqual(files["/home/user/example_input_dir/random stuff/nsfw"], 3)

    def test_simple_sort(self, mock_sorter_move: Mock):
        ip = create_test_input_path()

        sorter = ImageSorter(ip)
        sorter.output_dir = Path("/home/user/example_output_dir")

        sorter.sort()

        self.assertEqual(mock_sorter_move.call_count, 4)

    def test_recursive_sort(self, mock_sorter_move: Mock):
        ip = create_test_input_path()

        sorter = ImageSorter(ip)
        sorter.output_dir = Path("/home/user/example_output_dir")
        sorter.recursive = True

        sorter.sort()

        self.assertEqual(mock_sorter_move.call_count, 12)

    def test_cancel_sort(self, mock_sorter_move: Mock):
        ip = create_test_input_path()

        sorter = ImageSorter(ip)
        sorter.output_dir = Path("/home/user/example_output_dir")

        mock_sorter_move.side_effect = lambda file: time.sleep(1)

        sorter_thread = Thread(target=sorter.sort)
        sorter_thread.start()

        time.sleep(2)

        sorter.cancel()
        sorter_thread.join()

        self.assertGreaterEqual(mock_sorter_move.call_count, 2)
        self.assertLess(mock_sorter_move.call_count, 4)

@patch("exif_sort.sorter.ImageFile.move", mock_move)
class TestImageSorterMove(unittest.TestCase):

    def setUp(self):
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

    def test_simple_move(self):
        ip = create_test_input_path()

        def on_file_move(path, new_path, progress):
            self.assertEqual(new_path, Path("/home/user/example_output_dir", "2022/December/08", path.name))

        with patch("exif_sort.sorter.ImageFile.get_date_time") as mock_get_date_time:
            mock_get_date_time.return_value = datetime(2022, 12, 8, 15, 17, 49)

            sorter = ImageSorter(ip)
            sorter.output_dir = Path("/home/user/example_output_dir")

            sorter.on_move = on_file_move
            sorter.on_finish = Mock()

            sorter.sort()
            sorter.on_finish.called_once()

    def test_group_format(self):
        ip = create_test_input_path()

        def on_file_move(path, new_path, progress):
            self.assertEqual(new_path, Path("/home/user/example_output_dir", "2022/12", path.name))

        def on_file_move_2(path, new_path, progress):
            self.assertEqual(new_path, Path("/home/user/example_output_dir", "Year 2022/December/08", path.name))

        with patch("exif_sort.sorter.ImageFile.get_date_time") as mock_get_date_time:
            mock_get_date_time.return_value = datetime(2022, 12, 8, 15, 17, 49)

            sorter = ImageSorter(ip)
            sorter.output_dir = Path("/home/user/example_output_dir")

            sorter.group_format = "%Y/%m"
            sorter.on_move = on_file_move
            sorter.sort()

            sorter.group_format = "Year %Y/%B/%d"
            sorter.on_move = on_file_move_2
            sorter.sort()

    def test_rename_format(self):
        ip = create_test_input_path()

        def on_file_move(path, new_path, progress):
            self.assertEqual(new_path, Path("/home/user/example_output_dir", "2022/December/08", "08 December.jpg"))

        def on_file_move_2(path, new_path, progress):
            self.assertEqual(new_path, Path("/home/user/example_output_dir", path.name))

        with patch("exif_sort.sorter.ImageFile.get_date_time") as mock_get_date_time:
            mock_get_date_time.return_value = datetime(2022, 12, 8, 15, 17, 49)

            sorter = ImageSorter(ip)
            sorter.output_dir = Path("/home/user/example_output_dir")

            sorter.rename_format = "%d %B"
            sorter.on_move = on_file_move
            sorter.sort()

            mock_get_date_time.return_value = None
            
            sorter.sort_unknown = True
            sorter.on_move = on_file_move_2
            sorter.sort()

    def test_sort_unknown(self):
        ip = create_test_input_path()

        with patch("exif_sort.sorter.ImageFile.get_date_time") as mock_get_date_time:
            mock_get_date_time.side_effect = [
                datetime(2022, 12, 8, 15, 17, 49),
                None,
                None,
                datetime(2022, 12, 9, 16, 6, 23)
            ]

            sorter = ImageSorter(ip)
            sorter.output_dir = Path("/home/user/example_output_dir")
            sorter.sort_unknown = False

            sorter.on_move = Mock()
            sorter.on_skip = Mock()

            sorter.sort()

            self.assertEqual(sorter.on_move.call_count, 2)
            self.assertEqual(sorter.on_skip.call_count, 2)

            sorter.sort_unknown = True
            sorter.on_move = Mock()
            sorter.on_skip = Mock()

            sorter.sort()

            self.assertEqual(sorter.on_move.call_count, 4)
            self.assertEqual(sorter.on_skip.call_count, 0)

    def test_move_input_dir_no_permission(self):
        ip = create_test_input_path()
        ip.iterdir = Mock(side_effect=PermissionError)

        sorter = ImageSorter(ip)
        sorter.output_dir = Path("/home/user/example_output_dir")

        sorter.on_error = Mock()

        sorter.sort()

        self.assertEqual(sorter.on_error.call_count, 1)

    def test_move_error(self):
        exif_sort.sorter.ImageFile.move = Mock(side_effect=ImageMoveError("error_image.jpg", OSError))

        ip = create_test_input_path()

        with patch("exif_sort.sorter.ImageFile.get_date_time") as mock_get_date_time:
            mock_get_date_time.return_value = datetime(2022, 12, 8, 15, 17, 49)

            sorter = ImageSorter(ip)
            sorter.output_dir = Path("/home/user/example_output_dir")

            sorter.on_error = Mock()

            sorter.sort()

            self.assertEqual(sorter.on_error.call_count, 4)

@patch("exif_sort.sorter.ImageFile.get_date_time")
class TestImageSorterProgress(unittest.TestCase):

    def setUp(self):
        self.__ip = create_test_input_path()
        self.__progress_list = []

    def on_progress(self, *args):
        self.__progress_list.append(args[-1])

    @patch("exif_sort.sorter.ImageFile.move", lambda self, path: path)
    def test_move_all(self, mock_get_date_time: Mock):
        mock_get_date_time.return_value = datetime(2022, 12, 8, 15, 17, 49)

        sorter = ImageSorter(self.__ip)
        sorter.output_dir = Path("/home/user/example_output_dir")

        sorter.on_move = self.on_progress

        sorter.sort()

        self.assertEqual(self.__progress_list, [0.25, 0.5, 0.75, 1])

        self.__progress_list = []

        sorter.recursive = True
        sorter.sort()

        self.assertEqual(self.__progress_list, [1/12, 1/6, 0.25, 1/3, 5/12, 0.5, 7/12, 2/3, 0.75, 5/6, 11/12, 1])

    @patch("exif_sort.sorter.ImageFile.move", lambda self, path: path)
    def test_move_and_skip(self, mock_get_date_time: Mock):
        mock_get_date_time.side_effect = [
            datetime(2022, 12, 8, 15, 17, 49),
            None,
            None,
            datetime(2022, 12, 9, 16, 6, 23)
        ]

        sorter = ImageSorter(self.__ip)
        sorter.output_dir = Path("/home/user/example_output_dir")

        sorter.on_move = self.on_progress
        sorter.on_skip = self.on_progress

        sorter.sort()

        self.assertEqual(self.__progress_list, [0.25, 0.5, 0.75, 1])

    @patch("exif_sort.sorter.ImageFile.move")
    def test_some_errors(self, mock_move: Mock, mock_get_date_time: Mock):
        mock_get_date_time.return_value = datetime(2022, 12, 8, 15, 17, 49)

        sorter = ImageSorter(self.__ip)
        sorter.output_dir = Path("/home/user/example_output_dir")

        sorter.on_move = self.on_progress
        sorter.on_error = self.on_progress

        # ImageMoveError case
        mock_move.side_effect = [
            lambda self, path: path,
            lambda self, path: ImageMoveError(path, PermissionError()),
            lambda self, path: ImageMoveError(path, PermissionError()),
            lambda self, path: path,
        ]

        sorter.sort()

        self.assertEqual(self.__progress_list, [0.25, 0.5, 0.75, 1])

        # Not ImageMoveError related errors case
        self.__progress_list = []

        mock_move.side_effect = [
            lambda self, path: path,
            lambda self, path: path,
            RuntimeError,
            lambda self, path: path,
        ]

        sorter.sort()

        self.assertEqual(self.__progress_list, [0.25, 0.5, 1])

if __name__ == "__main__":
    unittest.main()
