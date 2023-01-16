"""Image sorting implementation."""

import shutil
import sys
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import Any, Callable, Optional, Sequence

from dateutil.parser import isoparse
from PIL import Image, UnidentifiedImageError


class ImageOpenError(Exception):
    """Raised if image couldn't be opened."""

    def __init__(self, path: Path):
        """Create new open exception with given path to file."""
        super().__init__(f"Couldn't open image ({path})")


class ImageMoveError(Exception):
    """Raised if image couldn't be moved."""

    def __init__(self, path: Path, reason: Exception):
        """Create new move exception with given path to file and the reason."""
        super().__init__(f"Couldn't move image ({path})")

        self.path = path
        self.reason: Exception = reason


class ImageFile:
    """Class for operating on image file."""

    def __init__(self, path: Path):
        """Create new read-only image file object."""
        self.__path = path
        self.__exif = None

    def get_date_time(self) -> Optional[datetime]:
        """Extract date of image from EXIF."""
        try:
            with Image.open(self.__path) as img:
                self.__exif = img.getexif()
        except (OSError, UnidentifiedImageError) as e:
            raise ImageOpenError(self.__path) from e

        if not self.__exif:
            return None

        date_time_str: str = self.__exif.get(306)  # 306 - DateTime

        if date_time_str is None or len(date_time_str) == 0:
            return None

        try:
            return datetime.strptime(date_time_str, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass  # try isoparse

        try:
            return isoparse(date_time_str)
        except ValueError:
            return None

    def move(self, output_path: Path) -> Path:
        """Move file to new location."""
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
            raise ImageMoveError(self.__path, e) from e

        return new_path


class ImageSorter:
    """Performs images sorting operation."""

    input_dir: Path
    output_dir: Path
    recursive: bool = False
    group_format: str = "%Y/%B/%d"
    sort_unknown: bool = False
    rename_format: Optional[str] = None

    on_finish: Callable
    on_skip: Callable[[Path, float], Any]
    on_move: Callable[[Path, Path, float], Any]
    on_error: Callable[[Exception, float], Any]

    __output_queue: Queue
    __dirs: list
    __cancelled: bool = False

    def __init__(self, input_dir: Path):
        """Create new sorter."""
        self.input_dir = input_dir
        self.output_dir = input_dir.joinpath("sort_output")

    def sort(self):
        """Start sorting task."""
        self.__output_queue = Queue()
        self.__dirs = []

        prepare_thread = Thread(target=self.__prepare, args=(self.input_dir,))
        prepare_thread.start()
        prepare_thread.join()

        self.__dirs.reverse()

        with ThreadPoolExecutor() as executor:
            futures = []
            for dir in self.__dirs:
                future = executor.submit(self.__sorting_task, dir["dir"])
                futures.append(future)

            self.__run_event_loop(futures)

        if getattr(self, "on_finish", False):
            self.on_finish()

    def __run_event_loop(self, futures: Sequence[Future]):
        while True:
            try:
                event = self.__output_queue.get(timeout=60)

                if event[0] == "move" and getattr(self, "on_move", False):
                    self.on_move(*event[1:])
                elif event[0] == "error" and getattr(self, "on_error", False):
                    self.on_error(*event[1:])
                elif event[0] == "skip" and getattr(self, "on_skip", False):
                    self.on_skip(*event[1:])
            except Empty:
                if getattr(self, "on_error", False):
                    self.on_error(
                        RuntimeError(
                            "empty-queue",
                            "No event received in last 60 seconds.",
                        ),
                        self.__get_progress(),
                    )

            if False not in [f.done() for f in futures] and self.__output_queue.empty():
                break

    def cancel(self) -> None:
        """Request cancellation of sorting task."""
        self.__cancelled = True

    def __prepare(self, dir: Path) -> None:
        """Prepare list of directories to sort and counts files."""
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
        """Start sorting loop."""
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
        except OSError as e:
            dir_data = self.__get_dir_data(dir)
            if dir_data:
                dir_data["progress"] = dir_data["files"]
            self.__trigger_event(("error", e))
        except Exception:  # pragma: no cover
            traceback.print_exc(file=sys.stderr)
            raise

        self.__trigger_event(("finish",))

    def __move(self, path: Path):
        """Determine new image path and moves the file."""
        img = ImageFile(path)

        try:
            date_time = img.get_date_time()
        except ImageOpenError:
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

    def __trigger_event(
        self, event_data: tuple, input_dir: Optional[Path] = None
    ) -> None:
        """
        Triggers a sorter progress event.

        event_data is a tuple in a form of ("event_name", *event_args)
        where event_name is required.
        If input_dir is provided, progress on that directory is increased.
        """
        if input_dir:
            dir_data = self.__get_dir_data(input_dir)
            if dir_data:
                dir_data["progress"] += 1
        self.__output_queue.put((*event_data, self.__get_progress()))

    def __get_dir_data(self, dir: Path) -> Optional[dict]:
        """Return sorter data about specified directory."""
        dirset = {dir["dir"]: dir for dir in self.__dirs}
        if dir in dirset:
            return dirset[dir]
        return None

    def __get_progress(self) -> float:
        """Return total progress on sorting as number in range of [0;1]."""
        files, progress = 0, 0
        for dir in self.__dirs:
            files += dir["files"]
            progress += dir["progress"]

        if files == 0:
            return 1

        return progress / files
