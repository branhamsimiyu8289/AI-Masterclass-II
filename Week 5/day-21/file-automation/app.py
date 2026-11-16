"""Safe, command-line helpers for common file automation tasks."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import Sequence


CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif"},
    "Documents": {".pdf", ".docx", ".txt", ".xlsx"},
    "Scripts": {".py", ".js", ".html"},
    "Other": set(),
}


def _require_directory(folder: Path) -> None:
    if not folder.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a folder: {folder}")


def _require_file(source: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"File does not exist: {source}")
    if not source.is_file():
        raise ValueError(f"Not a file: {source}")


def _validate_operations(
    operations: list[tuple[Path, Path]], *, allow_missing_parents: bool = False
) -> None:
    destinations: set[Path] = set()
    for source, destination in operations:
        if source.resolve() == destination.resolve():
            raise ValueError(f"Source and destination are the same: {source}")
        if destination.exists():
            raise FileExistsError(f"Destination already exists: {destination}")
        if destination in destinations:
            raise FileExistsError(f"Multiple files target the same path: {destination}")
        destinations.add(destination)

        parent = destination.parent
        if allow_missing_parents:
            while not parent.exists() and parent != parent.parent:
                parent = parent.parent
        if not parent.is_dir():
            raise NotADirectoryError(f"Destination folder does not exist: {parent}")


def _perform_operations(
    operations: list[tuple[Path, Path]], action: str, dry_run: bool
) -> list[str]:
    messages = []
    for source, destination in operations:
        verb = "Would " if dry_run else ""
        messages.append(f"{verb}{action}: {source} -> {destination}")
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if action == "copy":
                shutil.copy2(source, destination)
            elif action == "move":
                shutil.move(str(source), str(destination))
            elif action == "rename":
                source.rename(destination)
    return messages


def list_files(folder: Path) -> list[Path]:
    _require_directory(folder)
    return sorted(folder.iterdir(), key=lambda path: path.name.casefold())


def check_path(path: Path) -> bool:
    return path.exists()


def create_folder(folder: Path, dry_run: bool = True) -> str:
    if folder.exists() and not folder.is_dir():
        raise NotADirectoryError(f"Not a folder: {folder}")
    if dry_run:
        return f"Would create folder: {folder}"
    folder.mkdir(parents=True, exist_ok=True)
    return f"Created folder: {folder}"


def copy_file(source: Path, destination: Path, dry_run: bool = True) -> str:
    _require_file(source)
    _validate_operations([(source, destination)])
    return _perform_operations([(source, destination)], "copy", dry_run)[0]


def move_file(source: Path, destination: Path, dry_run: bool = True) -> str:
    _require_file(source)
    _validate_operations([(source, destination)])
    return _perform_operations([(source, destination)], "move", dry_run)[0]


def organize_files(folder: Path, dry_run: bool = True) -> list[str]:
    _require_directory(folder)
    operations = []
    for source in sorted(folder.iterdir(), key=lambda path: path.name.casefold()):
        if not source.is_file():
            continue
        extension = source.suffix.lower()
        category = next(
            (name for name, extensions in CATEGORIES.items() if extension in extensions),
            "Other",
        )
        category_folder = folder / category
        if category_folder.exists() and not category_folder.is_dir():
            raise NotADirectoryError(f"Not a category folder: {category_folder}")
        operations.append((source, category_folder / source.name))

    _validate_operations(operations, allow_missing_parents=True)
    if not operations:
        return ["No files to organize."]
    return _perform_operations(operations, "move", dry_run)


def backup_reports(
    source_folder: Path, archive_folder: Path, dry_run: bool = True
) -> list[str]:
    _require_directory(source_folder)
    if archive_folder.exists() and not archive_folder.is_dir():
        raise NotADirectoryError(f"Not an archive folder: {archive_folder}")
    month_folder = archive_folder / datetime.now().strftime("%Y-%m")
    if month_folder.exists() and not month_folder.is_dir():
        raise NotADirectoryError(f"Not an archive folder: {month_folder}")

    reports = sorted(
        (
            path
            for path in source_folder.iterdir()
            if path.is_file() and path.suffix.lower() == ".xlsx"
        ),
        key=lambda path: path.name.casefold(),
    )
    operations = [(report, month_folder / report.name) for report in reports]
    _validate_operations(operations, allow_missing_parents=True)
    if not operations:
        return ["No .xlsx reports found."]
    return _perform_operations(operations, "copy", dry_run)


def rename_photos(
    folder: Path, order_number: str, dry_run: bool = True
) -> list[str]:
    _require_directory(folder)
    invalid_characters = '<>:"/\\|?*'
    if (
        not order_number.strip()
        or order_number in {".", ".."}
        or order_number.endswith((" ", "."))
        or any(
            ord(character) < 32 or character in invalid_characters
            for character in order_number
        )
    ):
        raise ValueError("Order number must be a valid filename component.")

    photos = sorted(
        (path for path in folder.iterdir() if path.is_file()),
        key=lambda path: path.name.casefold(),
    )
    operations = []
    for index, photo in enumerate(photos, start=1):
        destination = folder / f"{order_number}_photo_{index:02d}{photo.suffix}"
        if photo.resolve() != destination.resolve():
            operations.append((photo, destination))
    _validate_operations(operations)
    if not operations:
        return ["Files are already named." if photos else "No files to rename."]
    return _perform_operations(operations, "rename", dry_run)


def _add_apply_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the operation (mutating commands preview by default)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview or perform common file automation tasks."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    list_parser = commands.add_parser("list", help="list a folder's contents")
    list_parser.add_argument("folder", type=Path)

    exists_parser = commands.add_parser("exists", help="check whether a path exists")
    exists_parser.add_argument("path", type=Path)

    mkdir_parser = commands.add_parser("mkdir", help="create a folder")
    mkdir_parser.add_argument("folder", type=Path)
    _add_apply_option(mkdir_parser)

    for name, help_text in (
        ("copy", "copy a file to a destination path"),
        ("move", "move a file to a destination path"),
    ):
        file_parser = commands.add_parser(name, help=help_text)
        file_parser.add_argument("source", type=Path)
        file_parser.add_argument("destination", type=Path)
        _add_apply_option(file_parser)

    organize_parser = commands.add_parser(
        "organize", help="sort files into category folders"
    )
    organize_parser.add_argument("folder", type=Path)
    _add_apply_option(organize_parser)

    backup_parser = commands.add_parser(
        "backup", help="copy .xlsx reports into a year-month archive folder"
    )
    backup_parser.add_argument("source_folder", type=Path)
    backup_parser.add_argument("archive_folder", type=Path)
    _add_apply_option(backup_parser)

    rename_parser = commands.add_parser(
        "rename-photos", help="rename files using an order number"
    )
    rename_parser.add_argument("folder", type=Path)
    rename_parser.add_argument("order_number")
    _add_apply_option(rename_parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    dry_run = not getattr(args, "apply", False)

    try:
        if args.command == "list":
            for path in list_files(args.folder):
                print(path.name)
        elif args.command == "exists":
            print("Path found." if check_path(args.path) else "Path not found.")
        elif args.command == "mkdir":
            print(create_folder(args.folder, dry_run))
        elif args.command == "copy":
            print(copy_file(args.source, args.destination, dry_run))
        elif args.command == "move":
            print(move_file(args.source, args.destination, dry_run))
        elif args.command == "organize":
            messages = organize_files(args.folder, dry_run)
            if not dry_run:
                print(f"Organized files in {args.folder}.")
            for message in messages:
                print(message)
        elif args.command == "backup":
            messages = backup_reports(args.source_folder, args.archive_folder, dry_run)
            for message in messages:
                print(message)
        elif args.command == "rename-photos":
            messages = rename_photos(args.folder, args.order_number, dry_run)
            for message in messages:
                print(message)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
