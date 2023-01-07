from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime
from pathlib import Path
import shutil
from threading import Thread
from queue import Queue
from typing import Callable

from PIL import Image

class ImageOpenError(Exception):
    """Raised if image couldn't be opened."""
    def __init__(self, path: Path):
        super().__init__(f"Couldn't open image ({path})")

class ImageMoveError(Exception):
    """Raised if image couldn't be moved."""
    def __init__(self, path: Path, reason: Exception):
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

        if date_time_str is None or len(date_time_str) == 0:
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

        self.__output_queue = None
        self.__dirs = None
        self.__cancelled = False

        self.on_finish: Callable = None
        self.on_skip: Callable[[Path, float], Any] = None
        self.on_move: Callable[[Path, Path, float], Any] = None
        self.on_error: Callable[[Exception, float], Any] = None

    def sort(self):
        """Starts sorting task."""
        self.__output_queue = Queue()
        self.__dirs = []

        prepare_thread = Thread(target=self.__prepare, args=(self.input_dir,))
        prepare_thread.start()
        prepare_thread.join()

        self.__dirs.reverse()

        with ThreadPoolExecutor() as executor:
            futures = []
            for dir in self.__dirs:
                f = executor.submit(self.__sorting_task, dir["dir"])
                futures.append(f)

            while True:
                event = self.__output_queue.get()

                if event[0] == "move" and self.on_move is not None:
                    self.on_move(*event[1:])
                elif event[0] == "error" and self.on_error is not None:
                    self.on_error(*event[1:])
                elif event[0] == "skip" and self.on_skip is not None:
                    self.on_skip(*event[1:])

                if False not in [f.done() for f in futures] and self.__output_queue.empty():
                    break

        if self.on_finish is not None:
            self.on_finish()

    def cancel(self) -> None:
        """Requests cancellation of sorting task."""
        self.__cancelled = True

    def __prepare(self, dir: Path) -> None:
        """Prepares list of directories to sort and counts files."""
        try:
            files = 0
            for file in dir.iterdir():
                if self.__cancelled:
                    break

                if file.is_dir():
                    if self.recursive:
                        self.__prepare(file)
                    else:
                        continue
                else:
                    files += 1
            self.__dirs.append({"dir": dir, "files": files, "progress": 0})
        except OSError as e:
            self.__trigger_event(("error", e))

    def __sorting_task(self, dir: Path):
        """Starts sorting loop."""
        try:
            for file in dir.iterdir():
                if self.__cancelled:
                    break

                if file.is_dir():
                    continue

                try:
                    self.__move(file)
                except ImageMoveError as e:
                    self.__trigger_event(("error", e), dir)
        except Exception as e:
            dir_data = self.__get_dir_data(dir)
            dir_data["progress"] = dir_data["files"]
            self.__trigger_event(("error", e))

        self.__trigger_event(("finish",))

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
            self.__trigger_event(("skip", path), path.parent)
            return

        output_path = output_path.joinpath(filename)

        new_path = img.move(output_path)

        self.__trigger_event(("move", path, new_path), path.parent)

    def __trigger_event(self, event_data: tuple, input_dir: Path=None) -> None:
        """
        Triggers a sorter progress event.

        event_data is a tuple in a form of ("event_name", *event_args)
        where event_name is required.
        If input_dir is provided, progress on that directory is increased.
        """
        if input_dir:
            self.__get_dir_data(input_dir)["progress"] += 1
        self.__output_queue.put((*event_data, self.__get_progress()))

    def __get_dir_data(self, dir: Path) -> dict:
        """Returns sorter data about specified directory."""
        dirset = { dir["dir"]: dir for dir in self.__dirs }
        if dir in dirset:
            return dirset[dir]
        return None

    def __get_progress(self) -> float:
        """Returns total progress on sorting as number in range of [0;1]."""
        files, progress = 0, 0
        for dir in self.__dirs:
            files += dir["files"]
            progress += dir["progress"]

        if files == 0:
            return 1

        return progress / files
