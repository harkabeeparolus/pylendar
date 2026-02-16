import datetime

class LunarDate:
    def __init__(
        self, year: int, month: int, day: int, isLeapMonth: bool = False
    ) -> None: ...
    def toSolarDate(self) -> datetime.date: ...
