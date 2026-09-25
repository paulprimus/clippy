from dataclasses import dataclass
from typing import Literal


RecordType = Literal["1", "2", "u", "?", "!"]


@dataclass(frozen=True, slots=True)
class Change:
    """Ein Änderungseintrag aus `git status --porcelain=v2`."""

    path: str
    record_type: RecordType
    xy: str | None = None
    sub: str | None = None
    modes: tuple[str, ...] = ()
    object_ids: tuple[str, ...] = ()
    original_path: str | None = None
    score: str | None = None

    def __post_init__(self) -> None:
        if self.record_type not in ("1", "2", "u", "?", "!"):
            raise ValueError(f"Nicht unterstützter Porcelain-v2-Eintragstyp: {self.record_type!r}")
        if not self.path:
            raise ValueError("Der Pfad darf nicht leer sein.")

        if self.record_type in ("?", "!"):
            if self.xy is not None or self.sub is not None:
                raise ValueError("Nicht versionierte und ignorierte Einträge besitzen weder ein xy- noch ein sub-Feld.")
            if self.modes or self.object_ids or self.original_path or self.score:
                raise ValueError("Nicht versionierte und ignorierte Einträge besitzen keine weiteren Felder.")
            return

        if self.xy is None or len(self.xy) != 2 or any(
            status not in ".MTADRCU" for status in self.xy
        ):
            raise ValueError("xy muss aus zwei gültigen Statuszeichen des Porcelain-v2-Formats bestehen.")
        if self.sub is None or not (
            self.sub == "N..."
            or (
                len(self.sub) == 4
                and self.sub[0] == "S"
                and self.sub[1] in ".C"
                and self.sub[2] in ".M"
                and self.sub[3] in ".U"
            )
        ):
            raise ValueError("sub muss 'N...' oder einen gültigen Submodulstatus enthalten.")

        if self.record_type in ("1", "2"):
            if len(self.modes) != 3 or len(self.object_ids) != 2:
                raise ValueError("Normale und umbenannte Einträge benötigen 3 Modi und 2 Objekt-IDs.")
        elif len(self.modes) != 4 or len(self.object_ids) != 3:
            raise ValueError("Konflikteinträge benötigen 4 Modi und 3 Objekt-IDs.")

        if self.record_type == "2":
            if not self.original_path or self.score is None:
                raise ValueError("Umbenannte oder kopierte Einträge benötigen den ursprünglichen Pfad und einen Ähnlichkeitswert.")
            if len(self.score) < 2 or self.score[0] not in "RC" or not self.score[1:].isdigit():
                raise ValueError("Der Ähnlichkeitswert muss ein Umbenennungs- oder Kopierwert sein, zum Beispiel 'R100'.")
            if int(self.score[1:]) > 100:
                raise ValueError("Der Ähnlichkeitswert darf 100 nicht überschreiten.")
        elif self.original_path is not None or self.score is not None:
            raise ValueError("Nur umbenannte oder kopierte Einträge besitzen einen ursprünglichen Pfad und einen Ähnlichkeitswert.")

    @property
    def index_status(self) -> str | None:
        """Der Status des Index-Eintrags (das X-Zeichen in XY)."""
        return self.xy[0] if self.xy is not None else None

    @property
    def worktree_status(self) -> str | None:
        """Der Status des Arbeitsbaum-Eintrags (das Y-Zeichen in XY)."""
        return self.xy[1] if self.xy is not None else None

    @property
    def is_submodule(self) -> bool:
        return self.sub is not None and self.sub.startswith("S")
