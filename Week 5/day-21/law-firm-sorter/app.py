"""Safe, command-line helpers for law firm document sorting and file automation."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import Sequence


CATEGORIES = {
    "Contracts": {".docx", ".doc"},
    "Evidence": {".jpg", ".jpeg", ".png"},
    "Filings": {".pdf"},
    "Correspondence": {".txt", ".eml"},
    "Other": set(),
}

DEFAULT_LOG_FILENAME = "sort_log.txt"

SAMPLE_FILES: dict[str, str] = {
    "Contract_FINAL_v3.docx": "Final signed agreement for commercial tenancy on Moi Avenue.",
    "Commercial_Lease_Agreement.doc": "Draft commercial lease terms and conditions.",
    "Employment_Contract_Signed.docx": "Executed employment agreement with confidentiality clauses.",
    "IMG_4827.jpg": "Photo of vehicle collision at Haile Selassie roundabout.",
    "Accident_Scene_Photo_01.jpeg": "Scene photo showing road skid marks and traffic signals.",
    "Scanned_National_ID.png": "Scanned national ID card of client.",
    "scan001.pdf": "Scanned certificate of incorporation and PIN certificate.",
    "High_Court_Petition_2026.pdf": "Petition filed at the High Court of Kenya, Milimani Law Courts.",
    "Affidavit_of_Service.pdf": "Sworn affidavit of service confirmed by process server.",
    "Client_Consultation_Notes.txt": "Notes from initial client intake conference on 14 Nov 2026.",
    "Settlement_Offer_Thread.eml": "Email exchange regarding out-of-court settlement terms.",
    "Court_Filing_Fee_Receipt.xlsx": "Spreadsheet listing disbursement fees paid via e-filing portal.",
    "Witness_Interview_Audio.mp3": "Audio recording of key eyewitness testimony.",
    "Case_Evidence_Archive.zip": "Compressed archive of background investigative files.",
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


def _format_log_entry(
    source: Path, destination: Path, timestamp: datetime | None = None
) -> str:
    current_time = (timestamp or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    return f"[{current_time}] {source.resolve()} -> {destination.resolve()}"


def _append_to_log(log_path: Path, entries: Sequence[str]) -> None:
    if not entries:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        for entry in entries:
            file.write(f"{entry}\n")


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
    operations: list[tuple[Path, Path]],
    action: str,
    dry_run: bool,
    *,
    log_path: Path | None = None,
) -> list[str]:
    messages = []
    log_entries = []
    for source, destination in operations:
        verb = "Would " if dry_run else ""
        messages.append(f"{verb}{action}: {source} -> {destination}")
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if action == "copy":
                shutil.copy2(source, destination)
            elif action == "move":
                shutil.move(str(source), str(destination))
                log_entries.append(_format_log_entry(source, destination))
            elif action == "rename":
                source.rename(destination)

    if not dry_run and log_path and log_entries:
        _append_to_log(log_path, log_entries)

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


def move_file(
    source: Path,
    destination: Path,
    dry_run: bool = True,
    *,
    log_path: Path | None = None,
) -> str:
    _require_file(source)
    _validate_operations([(source, destination)])
    return _perform_operations(
        [(source, destination)], "move", dry_run, log_path=log_path
    )[0]


def get_category_for_file(filename: str | Path) -> str:
    extension = Path(filename).suffix.lower()
    return next(
        (name for name, extensions in CATEGORIES.items() if extension in extensions),
        "Other",
    )


def sort_documents(
    folder: Path,
    dry_run: bool = True,
    *,
    log_file: Path | None = None,
) -> list[str]:
    _require_directory(folder)
    target_log_file = (log_file or (folder / DEFAULT_LOG_FILENAME)).resolve()

    operations: list[tuple[Path, Path]] = []
    for source in sorted(folder.iterdir(), key=lambda path: path.name.casefold()):
        if not source.is_file():
            continue
        if source.resolve() == target_log_file or source.name == DEFAULT_LOG_FILENAME:
            continue

        category = get_category_for_file(source)
        category_folder = folder / category
        if category_folder.exists() and not category_folder.is_dir():
            raise NotADirectoryError(f"Not a category folder: {category_folder}")

        operations.append((source, category_folder / source.name))

    _validate_operations(operations, allow_missing_parents=True)
    if not operations:
        return ["No files to organize."]

    return _perform_operations(
        operations, "move", dry_run, log_path=target_log_file
    )


def create_dummy_files(
    folder: Path,
    files: dict[str, str] | None = None,
) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    file_map = files if files is not None else SAMPLE_FILES
    created: list[Path] = []
    for filename, content in file_map.items():
        file_path = folder / filename
        file_path.write_text(content, encoding="utf-8")
        created.append(file_path)
    return created


def _add_apply_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the operation (mutating commands preview by default)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safe file automation and document sorting for law firm workflows."
    )
    commands = parser.add_subparsers(dest="command")

    list_parser = commands.add_parser("list", help="list a folder's contents")
    list_parser.add_argument("folder", type=Path)

    exists_parser = commands.add_parser("exists", help="check whether a path exists")
    exists_parser.add_argument("path", type=Path)

    mkdir_parser = commands.add_parser("mkdir", help="create a folder")
    mkdir_parser.add_argument("folder", type=Path)
    _add_apply_option(mkdir_parser)

    copy_parser = commands.add_parser("copy", help="copy a file to a destination path")
    copy_parser.add_argument("source", type=Path)
    copy_parser.add_argument("destination", type=Path)
    _add_apply_option(copy_parser)

    move_parser = commands.add_parser("move", help="move a file to a destination path")
    move_parser.add_argument("source", type=Path)
    move_parser.add_argument("destination", type=Path)
    move_parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="path to log file (logs move when applied)",
    )
    _add_apply_option(move_parser)

    for cmd_name in ("sort", "organize"):
        sort_parser = commands.add_parser(
            cmd_name,
            help="sort client documents into legal categories and log to sort_log.txt",
        )
        sort_parser.add_argument("folder", type=Path)
        sort_parser.add_argument(
            "--log-file",
            type=Path,
            default=None,
            help="optional path to sort log (default: <folder>/sort_log.txt)",
        )
        _add_apply_option(sort_parser)

    dummy_parser = commands.add_parser(
        "create-dummy",
        help="populate a folder with realistic dummy legal files for testing",
    )
    dummy_parser.add_argument("folder", type=Path)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

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
            print(
                move_file(
                    args.source,
                    args.destination,
                    dry_run,
                    log_path=args.log_file,
                )
            )
        elif args.command in ("sort", "organize"):
            messages = sort_documents(
                args.folder,
                dry_run=dry_run,
                log_file=args.log_file,
            )
            if not dry_run:
                log_dest = (args.log_file or (args.folder / DEFAULT_LOG_FILENAME)).resolve()
                print(f"Organized documents in {args.folder}.")
                print(f"Audit log written to: {log_dest}")
            for message in messages:
                print(message)
        elif args.command == "create-dummy":
            created_files = create_dummy_files(args.folder)
            print(f"Created {len(created_files)} dummy files in {args.folder}:")
            for file_path in created_files:
                print(f"  - {file_path.name}")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
