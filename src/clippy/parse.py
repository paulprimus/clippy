"""Einlesen von `git status --porcelain=v2`-Ausgaben in `Change`-Objekte."""

from collections.abc import Iterable, Iterator

from clippy.change import Change


def parse_line(line: str) -> Change | None:
    """Wandelt eine Zeile aus `git status --porcelain=v2` in ein `Change`-Objekt um.

    Branch-Header-Zeilen (beginnend mit `#`) sind keine Änderungen und werden
    mit `None` übersprungen. Leere Zeilen werden ebenfalls übersprungen.
    """
    line = line.rstrip("\n")
    if not line or line.startswith("#"):
        return None

    record_type, _, rest = line.partition(" ")
    if record_type not in ("1", "2", "u", "?", "!"):
        raise ValueError(f"Nicht unterstützte Porcelain-v2-Zeile: {line!r}")

    if record_type in ("?", "!"):
        if not rest:
            raise ValueError(f"Zeile enthält keinen Pfad: {line!r}")
        return Change(path=rest, record_type=record_type)

    if record_type == "2":
        fields = rest.split(" ", 7)
        if len(fields) != 8:
            raise ValueError(f"Zeile hat nicht genügend Felder für einen Rename/Copy-Eintrag: {line!r}")
        xy, sub, m_h, m_i, m_w, h_h, h_i, tail = fields
        score, _, paths = tail.partition(" ")
        path, sep, original_path = paths.partition("\t")
        if not sep:
            raise ValueError(f"Rename/Copy-Eintrag benötigt Pfad und Ursprungspfad, getrennt durch Tab: {line!r}")
        return Change(
            path=path,
            record_type=record_type,
            xy=xy,
            sub=sub,
            modes=(m_h, m_i, m_w),
            object_ids=(h_h, h_i),
            original_path=original_path,
            score=score,
        )

    if record_type == "1":
        fields = rest.split(" ", 7)
        if len(fields) != 8:
            raise ValueError(f"Zeile hat nicht genügend Felder für einen normalen Eintrag: {line!r}")
        xy, sub, m_h, m_i, m_w, h_h, h_i, path = fields
        return Change(
            path=path,
            record_type=record_type,
            xy=xy,
            sub=sub,
            modes=(m_h, m_i, m_w),
            object_ids=(h_h, h_i),
        )

    # record_type == "u"
    fields = rest.split(" ", 9)
    if len(fields) != 10:
        raise ValueError(f"Zeile hat nicht genügend Felder für einen Unmerged-Eintrag: {line!r}")
    xy, sub, m1, m2, m3, m_w, h1, h2, h3, path = fields
    return Change(
        path=path,
        record_type=record_type,
        xy=xy,
        sub=sub,
        modes=(m1, m2, m3, m_w),
        object_ids=(h1, h2, h3),
    )


def parse(lines: Iterable[str]) -> Iterator[Change]:
    """Liest mehrere Porcelain-v2-Zeilen (z. B. `sys.stdin`) ein und liefert die enthaltenen `Change`-Objekte."""
    for line in lines:
        change = parse_line(line)
        if change is not None:
            yield change
