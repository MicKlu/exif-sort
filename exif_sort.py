#!/usr/bin/python3

import os
from pathlib import Path
from PIL import Image
import sys

__version__ = "0.1.0"

class ImageOpenError(Exception):
    def __init__(self, path):
        super().__init__(f"Couldn't open image ({path})")

class ImageFile:
    def __init__(self, path: str):
        self.__path = path

        try:
            img = Image.open(path)
            self.__exif = img.getexif()

            img.close()
        except:
            raise ImageOpenError(self.__path)

    def get_date_time(self) -> list:
        date_time_str: str = self.__exif.get(306)

        if len(date_time_str) == 0:
            return None

        [date, time] = date_time_str.split(" ")

        return date.split(":") + time.split(":")

images_dir = Path(sys.argv[1])
for file in images_dir.iterdir():
    if file.is_dir():
        continue

    try:
        img = ImageFile(file)
        print(f"{file}: {img.get_date_time()}")
    except:
        pass