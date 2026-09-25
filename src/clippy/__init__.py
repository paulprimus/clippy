import argparse
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable

from clippy.change import Change
from clippy.parse import parse

_RECORD_TYPE_LABELS = {
    "1": "normale Änderung",
    "2": "Umbenennung/Kopie",
    "u": "nicht zusammengeführt (Konflikt)",
    "?": "nicht versioniert",
    "!": "ignoriert",
}

_STATUS_LABELS = {
    ".": "unverändert",
    "M": "modifiziert",
    "T": "Typänderung",
    "A": "hinzugefügt",
    "D": "gelöscht",
    "R": "umbenannt",
    "C": "kopiert",
    "U": "konfliktbehaftet",
}


def format_change_short(change: Change) -> str:
    """Formatiert einen `Change` als kompakte Zeile, analog zu `git status --short`."""
    if change.record_type == "?":
        status = "??"
    elif change.record_type == "!":
        status = "!!"
    else:
        status = change.xy

    if change.record_type == "2":
        return f"{status} {change.original_path} -> {change.path}"
    return f"{status} {change.path}"


def format_change_long(chg: Change) -> str:
    """Formatiert einen `Change` als ausführlichen, mehrzeiligen Block."""
    lines = [f"Pfad: {chg.path}"]
    if chg.record_type == "2":
        lines.append(f"Ursprünglicher Pfad: {chg.original_path}")
    lines.append(f"Typ: {_RECORD_TYPE_LABELS[chg.record_type]}")
    if chg.record_type == "2":
        lines.append(f"Ähnlichkeit: {chg.score}")

    if chg.record_type not in ("?", "!"):
        index_status = chg.index_status
        worktree_status = chg.worktree_status
        assert index_status is not None and worktree_status is not None
        index_label = _STATUS_LABELS[index_status]
        worktree_label = _STATUS_LABELS[worktree_status]
        lines.append(f"Index: {index_label} ({index_status})")
        lines.append(f"Arbeitsverzeichnis: {worktree_label} ({worktree_status})")
        if chg.is_submodule:
            lines.append(f"Submodul: ja ({chg.sub})")
        else:
            lines.append("Submodul: nein")

    return "\n".join(lines)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clippy",
        description="Liest `git status --porcelain=v2` von stdin und gibt die Änderungen formatiert aus.",
    )
    parser.add_argument(
        "--output",
        choices=("short", "long"),
        default="short",
        help="Ausgabeformat: 'short' für eine kompakte Zeile pro Änderung, "
        "'long' für einen ausführlichen Block pro Änderung (Standard: long).",
    )
    parser.add_argument(
        "--path",
        metavar="REGEX",
        help="Optionaler Regex, um nur Änderungen an Pfaden auszugeben, die auf den Regex passen. "
        "Bei Umbenennungen wird der ursprüngliche Pfad ebenfalls berücksichtigt.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Speichert alle passenden Pfade durch Leerzeichen getrennt in der Zwischenablage.",
    )
    return parser.parse_args(argv)


def _copy_to_clipboard(text: str) -> None:
    if sys.platform == "win32":
        candidates = (("clip",),)
    elif sys.platform == "darwin":
        candidates = (("pbcopy",),)
    else:
        candidates = (
            ("wl-copy",),
            ("xclip", "-selection", "clipboard"),
            ("xsel", "--clipboard", "--input"),
        )

    command = next(
        (
            [executable, *candidate[1:]]
            for candidate in candidates
            if (executable := shutil.which(candidate[0]))
        ),
        None,
    )
    if command is None:
        raise RuntimeError("Kein unterstütztes Zwischenablage-Programm gefunden.")
    subprocess.run(command, input=text, text=True, check=True)


def _format_changes(changes: Iterable[Change], output: str) -> Iterable[str]:
    if output == "short":
        for change in changes:
            yield format_change_short(change)
    else:
        first = True
        for change in changes:
            if not first:
                yield ""
            first = False
            yield format_change_long(change)


def _matches_path(chg: Change, pattern: re.Pattern[str] | None) -> bool:
    """Prüft, ob der Pfad (oder bei Umbenennungen der ursprüngliche Pfad) auf den Regex passt."""
    if pattern is None:
        return True
    if pattern.search(chg.path):
        return True
    return chg.record_type == "2" and bool(pattern.search(chg.original_path))


def main() -> None:
    args = _parse_args()
    pattern = re.compile(args.path) if args.path else None
    changes = [change for change in parse(sys.stdin) if _matches_path(change, pattern)]
    if args.save:
        _copy_to_clipboard(" ".join(change.path for change in changes))
    for line in _format_changes(changes, args.output):
        print(line)


if __name__ == "__main__":
    main()
