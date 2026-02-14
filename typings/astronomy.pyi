import datetime

class Time:
    @staticmethod
    def Make(
        year: int, month: int, day: int, hour: int, minute: int, second: float
    ) -> Time: ...
    @staticmethod
    def AddDays(time: Time, days: float) -> Time: ...
    def Utc(self) -> datetime.datetime: ...

class SeasonInfo:
    mar_equinox: Time
    jun_solstice: Time
    sep_equinox: Time
    dec_solstice: Time

def Seasons(year: int) -> SeasonInfo: ...
def SearchMoonPhase(
    targetLon: float, startTime: Time, limitDays: float
) -> Time | None: ...
