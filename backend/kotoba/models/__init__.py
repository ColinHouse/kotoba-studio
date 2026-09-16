"""ORM models, grouped by domain. See docs/superpowers/specs/2026-09-15-kotoba-studio-design.md §4.

Importing this package registers every mapper, which Alembic's autogenerate and
SQLAlchemy's string-based relationship resolution both rely on.
"""

from kotoba.models.base import Base, UTCDateTime, utcnow
from kotoba.models.capture import CaptureSession, Line, Source
from kotoba.models.reference import DictEntry, DictForm, Dictionary, TermFrequency, TermPitch
from kotoba.models.review import Card, Device, ReviewLog
from kotoba.models.system import LlmCall, Setting
from kotoba.models.vocabulary import Encounter, Sense, Term

__all__ = [
    "Base",
    "CaptureSession",
    "Card",
    "DictEntry",
    "DictForm",
    "Device",
    "Dictionary",
    "Encounter",
    "Line",
    "LlmCall",
    "ReviewLog",
    "Sense",
    "Setting",
    "Source",
    "Term",
    "TermFrequency",
    "TermPitch",
    "UTCDateTime",
    "utcnow",
]
