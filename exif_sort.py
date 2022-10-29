#!/usr/bin/python3

from datetime import datetime
import locale
import os
from pathlib import Path
from PIL import Image
import sys

__version__ = "0.1.0"

class ImageOpenError(Exception):
    """Raised if image couldn't be opened"""

    def __init__(self, path):
        super().__init__(f"Couldn't open image ({path})")

class ImageFile:
    """Class for operating on image file"""

    def __init__(self, path: Path):
        self.__path = path

        try:
            img = Image.open(path)
            self.__exif = img.getexif()

            img.close()
        except:
            raise ImageOpenError(self.__path)

    def get_date_time(self) -> datetime:
        date_time_str: str = self.__exif.get(306)

        if len(date_time_str) == 0:
            return None

        return datetime.strptime(date_time_str, "%Y:%m:%d %H:%M:%S")

    def move(self):
        pass

class ImageSorter:
    """Performs images sorting operation"""

    def __init__(self, input_dir: Path):
        self.input_dir = input_dir
        self.output_dir = input_dir.joinpath("sort_output")
        self.recursive = False
        self.group_format = "%Y/%B/%d"

    def sort(self):
        for file in self.input_dir.iterdir():
            if file.is_dir():
                if self.recursive:
                    # If recursive create new recursive sorter and perform sorting on directory
                    img_sorter = ImageSorter(file)
                    img_sorter.output_dir = self.output_dir
                    img_sorter.recursive = self.recursive
                    img_sorter.group_format = self.group_format

                    img_sorter.sort()
                else:
                    continue

            try:
                img = ImageFile(file)
                print(f"{file}")
                print(f"  {img.get_date_time().strftime(self.group_format)}")
            except:
                pass

if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "")

    # Initiate Image Sorter
    img_sorter = ImageSorter(Path(sys.argv[1]))
    # img_sorter.output_dir = output_dir
    # img_sorter.recursive = True
    # img_sorter.group_format = group_format

    img_sorter.sort()