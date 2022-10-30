#!/usr/bin/python3

import copy
from datetime import datetime
import locale
import os
from pathlib import Path
from PIL import Image
import shutil
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

        print(f"{self.__path} -> {output_path}")
        # output_path.parent.mkdir(parents=True, exist_ok=True)
        # shutil.copy(self.__path, output_path)
        # shutil.move(self.__path, output_path)

class ImageSorter:
    """Performs images sorting operation"""

    def __init__(self, input_dir: Path):
        self.input_dir = input_dir
        self.output_dir = input_dir.joinpath("sort_output")
        self.recursive = False
        self.group_format = "%Y/%B/%d"
        self.sort_unknown = False

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

        if date_time is not None:
            output_path = self.output_dir.joinpath(date_time.strftime(self.group_format))
            output_path = output_path.joinpath(path.name)
        elif date_time is None and self.sort_unknown:
            output_path = self.output_dir.joinpath(path.name)
        else:
            return

        img.move(output_path)

if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "")

    # Initiate Image Sorter
    img_sorter = ImageSorter(Path(sys.argv[1]))
    # img_sorter.output_dir = output_dir
    # img_sorter.recursive = True
    # img_sorter.group_format = group_format
    # img_sorter.sort_unknown = True

    img_sorter.sort()