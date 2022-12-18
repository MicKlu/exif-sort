from datetime import datetime
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from PIL import UnidentifiedImageError

from exif_sort.sorter import ImageFile, ImageOpenError, ImageMoveError
from exif_sort.sorter import Image

class ImageFileGetDateCase(unittest.TestCase):

    def create_image(self, exif_date = "") -> Mock:
        mock_image = Mock()

        mock_exif = Mock()
        mock_exif.get.return_value = exif_date

        mock_image.getexif.return_value = mock_exif

        return mock_image

    @patch.object(Image, "open")
    def test_file_has_exif(self, mock_open: Mock):
        mock_open.return_value = self.create_image(datetime.now().strftime("%Y:%m:%d %H:%M:%S"))
        
        img = ImageFile("mock_file.jpg")
        date_time = img.get_date_time()

        self.assertEqual(date_time, datetime.now().replace(microsecond=0))

    @patch.object(Image, "open")
    def test_file_has_not_exif(self, mock_open: Mock):
        mock_open.return_value = self.create_image()

        img = ImageFile("mock_file.bmp")
        date_time = img.get_date_time()
        self.assertIsNone(date_time)

    @patch.object(Image, "open", side_effect=[FileNotFoundError, UnidentifiedImageError, PermissionError])
    def test_file_open_error(self, mock_open: Mock):

        img = ImageFile("not_existing_file.txt")
        with self.assertRaises(ImageOpenError):
            img.get_date_time()

        with self.assertRaises(ImageOpenError):
            img.get_date_time()

        with self.assertRaises(ImageOpenError):
            img.get_date_time()

@patch("exif_sort.sorter.shutil")
@patch.object(Path, "mkdir")
class ImageFileMoveCase(unittest.TestCase):

    def test_output_path_exists(self, mock_mkdir, mock_shutil):
        img = ImageFile("image.jpg")
        
        with patch.object(Path, "exists") as mock_exists:
            mock_exists.side_effect = [True, True, False]
            new_path = img.move(Path("/home/user/existing_path.jpg"))

        self.assertEqual(new_path, Path("/home/user/existing_path-2.jpg"))

    def test_output_path_no_extension(self, mock_mkdir, mock_shutil):
        img = ImageFile("image.jpg")
        
        with patch.object(Path, "exists", return_value=False):
            new_path = img.move(Path("/home/user/existing_path"))

        self.assertEqual(new_path, Path("/home/user/existing_path"))

    def test_image_move_error(self, mock_mkdir, mock_shutil):
        import exif_sort

        mock_mkdir.side_effect = PermissionError
        
        img = ImageFile("image.jpg")

        with self.assertRaises(ImageMoveError):
            img.move(Path("/home/user/existing_path"))

        mock_mkdir.side_effect = None
        mock_shutil.move.side_effect = PermissionError

        with self.assertRaises(ImageMoveError):
            img.move(Path("/home/user/existing_path"))

        mock_mkdir.side_effect = OSError
        mock_shutil.move.side_effect = None

        with self.assertRaises(ImageMoveError):
            img.move(Path("/home/user/existing_path"))

        mock_mkdir.side_effect = None
        mock_shutil.move.side_effect = OSError

        with self.assertRaises(ImageMoveError):
            img.move(Path("/home/user/existing_path"))

        mock_shutil.move.side_effect = FileNotFoundError

        with self.assertRaises(ImageMoveError):
            img.move(Path("/home/user/existing_path"))

if __name__ == "__main__":
    unittest.main()