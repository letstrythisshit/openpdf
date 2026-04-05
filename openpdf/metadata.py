"""DocumentMetadata dataclass and helpers."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DocumentMetadata:
    """Typed representation of PDF document metadata."""
    format: str = ""
    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: str = ""
    creator: str = ""
    producer: str = ""
    creationDate: str = ""
    modDate: str = ""
    trapped: str = ""
    encryption: str | None = None

    @classmethod
    def from_pike_dict(cls, d: dict) -> "DocumentMetadata":
        return cls(
            format=d.get("format", ""),
            title=d.get("title", ""),
            author=d.get("author", ""),
            subject=d.get("subject", ""),
            keywords=d.get("keywords", ""),
            creator=d.get("creator", ""),
            producer=d.get("producer", ""),
            creationDate=d.get("creationDate", ""),
            modDate=d.get("modDate", ""),
            trapped=d.get("trapped", ""),
            encryption=d.get("encryption", None),
        )

    def to_dict(self) -> dict:
        return {
            "format": self.format,
            "title": self.title,
            "author": self.author,
            "subject": self.subject,
            "keywords": self.keywords,
            "creator": self.creator,
            "producer": self.producer,
            "creationDate": self.creationDate,
            "modDate": self.modDate,
            "trapped": self.trapped,
            "encryption": self.encryption,
        }
