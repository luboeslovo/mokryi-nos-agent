"""Transport-neutral response contracts for agent text and documents."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentArtifact:
    path: Path
    filename: str
    mime_type: str
    delete_after_send: bool = True


@dataclass(frozen=True)
class AgentResponse:
    text: str
    documents: tuple[DocumentArtifact, ...] = ()
