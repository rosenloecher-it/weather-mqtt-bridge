import os
import pathlib
from datetime import datetime, timezone


class SetupTest:

    TEST_DIR = "__test__"

    @classmethod
    def get_froggit_test_time(cls):
        """related time to `load_froggit_mocked_html`"""
        # CurrTime "14:04 8/25/2019"
        local_timezone = datetime.now(timezone.utc).astimezone().tzinfo
        sample_time = datetime(2019, 8, 25, 14, 4, tzinfo=local_timezone)  # -1 min allowed
        return sample_time

    @classmethod
    def load_froggit_mocked_html(cls) -> str:
        curr_path = os.path.dirname(os.path.abspath(__file__))
        test_path = os.path.join(curr_path, "fetcher", "froggit_livedata.html")
        with open(test_path) as file:
            data = file.read().replace('\n', '')
            return data

    @classmethod
    def get_project_dir(cls) -> str:
        file_path = os.path.dirname(__file__)
        out = os.path.dirname(file_path)  # go up one time
        return out

    @classmethod
    def get_test_dir(cls) -> str:
        project_dir = cls.get_project_dir()
        out = os.path.join(project_dir, cls.TEST_DIR)
        return out

    @classmethod
    def get_test_path(cls, relative_path) -> str:
        return os.path.join(cls.get_test_dir(), relative_path)

    @classmethod
    def ensure_test_dir(cls) -> str:
        return cls.ensure_dir(cls.get_test_dir())

    @classmethod
    def ensure_clean_test_dir(cls) -> str:
        return cls.ensure_clean_dir(cls.get_test_dir())

    @classmethod
    def ensure_dir(cls, dirpath) -> str:
        exists = os.path.exists(dirpath)

        if exists and not os.path.isdir(dirpath):
            raise NotADirectoryError(dirpath)
        if not exists:
            os.makedirs(dirpath)

        return dirpath

    @classmethod
    def ensure_clean_dir(cls, dirpath) -> str:
        if not os.path.exists(dirpath):
            cls.ensure_dir(dirpath)
        else:
            cls.clean_dir_recursively(dirpath)

        return dirpath

    @classmethod
    def clean_dir_recursively(cls, path_in):
        dir_segments = pathlib.Path(path_in)
        if not dir_segments.is_dir():
            return
        for item in dir_segments.iterdir():
            if item.is_dir():
                cls.clean_dir_recursively(item)
                os.rmdir(item)
            else:
                item.unlink()
