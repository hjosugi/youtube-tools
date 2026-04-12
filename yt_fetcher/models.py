from dataclasses import dataclass

class AppError(RuntimeError):
    pass

@dataclass
class SubtitleRow:
    start: str
    end: str
    en: str

    @property
    def time_range(self) -> str:
        return f"{self.start} --> {self.end}"
