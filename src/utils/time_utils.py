import datetime

from tzlocal import get_localzone


class TimeUtils:

    @classmethod
    def now(cls) -> datetime.datetime:
        """overwrite/mock in test"""
        return datetime.datetime.now(tz=get_localzone())
