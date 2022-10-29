import os
import sys
from PIL import Image

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

    def get_date_time(self):
        date_time_str = self.__exif.get(306)

        if len(date_time_str) == 0:
            return None

        return date_time_str

files = os.listdir(sys.argv[1])
for file in files:
    path = f"{sys.argv[1]}/{file}"

    if os.path.isdir(path):
        continue

    try:
        img = ImageFile(path)
        print(f"{path}: {img.get_date_time()}")
    except:
        pass