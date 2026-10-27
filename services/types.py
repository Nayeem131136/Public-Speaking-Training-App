"""Small classes the services use to pass data to each other."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Word:
    word: str
    start: float
    end: float


@dataclass
class TranscriptResult:
    text: str
    words: List[Word]
    duration: Optional[float]  # length of the audio if the engine knows it
    engine: str  # "faster-whisper" or "mock"


@dataclass
class Pause:
    start: float
    end: float
    duration: float
    kind: str  # "short", "dramatic" or "long"


@dataclass
class FillerHit:
    word: str  # the filler word or phrase from the list, e.g. "you know"
    start: float
    end: float


@dataclass
class WpmSegment:
    start_sec: float
    end_sec: float
    wpm: float


@dataclass
class WpmResult:
    total_words: int
    wpm: float
    speaking_seconds: float
    segments: List[WpmSegment] = field(default_factory=list)
