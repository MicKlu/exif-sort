import copy
from datetime import datetime
from pathlib import Path
import shutil
from typing import Callable

from PIL import Image

class ImageOpenError(Exception):
    """Raised if image couldn't be opened."""
    def __init__(self, path):
        super().__init__(f"Couldn't open image ({path})")

class ImageMoveError(Exception):
    """Raised if image couldn't be moved."""
    def __init__(self, path, reason: Exception):
        super().__init__(f"Couldn't move image ({path})")

        self.path = path
        self.reason: Exception = reason

class ImageFile:
    """Class for operating on image file."""
    def __init__(self, path: Path):
        self.__path = path
        self.__exif = None

    def get_date_time(self) -> datetime:
        """Extracts date of image from EXIF."""
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

    def move(self, output_path: Path) -> Path:
        """Moves file to new location."""
        new_path = output_path

        i = 1
        while new_path.exists():
            filename = output_path.stem
            extention = output_path.suffix
            new_path = output_path.parent.joinpath(f"{filename}-{i}{extention}")
            i += 1

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(self.__path, new_path)
        except OSError as e:
            raise ImageMoveError(self.__path, e)

        return new_path

class ImageSorter:
    """Performs images sorting operation."""
    def __init__(self, input_dir: Path):
        self.input_dir: Path = input_dir
        self.output_dir: Path = input_dir.joinpath("sort_output")
        self.recursive: bool = False
        self.group_format: str = "%Y/%B/%d"
        self.sort_unknown: bool = False
        self.rename_format: str = None

        self.on_finish: Callable = None
        self.on_skip: Callable[Path, Any] = None
        self.on_move: Callable[[Path, Path], Any] = None
        self.on_error: Callable[Exception, Any] = None

    def sort(self):
        """Starts sorting loop."""
        try:
            for file in self.input_dir.iterdir():
                if file.is_dir():
                    if self.recursive:
                        # If recursive, create new recursive sorter and perform sorting on directory
                        img_sorter = copy.copy(self)
                        img_sorter.input_dir = file
                        img_sorter.on_error = self.on_error
                        img_sorter.sort()
                    else:
                        continue
                else:
                    try:
                        self.__move(file)
                    except ImageMoveError as e:
                        if self.on_error is not None:
                            self.on_error(e)
        except OSError as e:
            if self.on_error is not None:
                self.on_error(e)

        if self.on_finish is not None:
            self.on_finish()


    def __move(self, path: Path):
        """Determines new image path and moves the file."""
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
            if self.on_skip is not None:
                self.on_skip(path)
            return

        output_path = output_path.joinpath(filename)

        new_path = img.move(output_path)

        if self.on_move is not None:
            self.on_move(path, new_path)
