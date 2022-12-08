from datetime import datetime
from pathlib import Path
import unittest
from unittest.mock import Mock, patch, create_autospec

from exif_sort.sorter import ImageSorter

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
    

@patch("exif_sort.sorter.ImageFile.move", mock_move)
class TestImageSorterMove(unittest.TestCase):
    def test_simple_move(self):
        ip = create_test_input_path()

        def on_file_move(path, new_path):
            self.assertEqual(new_path, Path("/home/user/example_output_dir", "2022/December/08", path.name))

        with patch("exif_sort.sorter.ImageFile.get_date_time") as mock_get_date_time:
            mock_get_date_time.return_value = datetime(2022, 12, 8, 15, 17, 49)

            sorter = ImageSorter(ip)
            sorter.output_dir = Path("/home/user/example_output_dir")

            sorter.on_move = on_file_move

            sorter.sort()

if __name__ == "__main__":
    unittest.main()