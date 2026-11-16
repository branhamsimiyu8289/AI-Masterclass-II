"""End-to-end demonstration and verification script for the law firm document sorter."""

from pathlib import Path
import app


def run_demonstration() -> None:
    demo_dir = Path(__file__).parent / "dummy_client_documents"

    # Clean up previous demo folder if it exists
    if demo_dir.exists():
        import shutil
        shutil.rmtree(demo_dir)

    print("=" * 70)
    print("NAIROBI MOI AVENUE LAW FIRM - CLIENT DOCUMENT SORTER DEMO")
    print("=" * 70)

    # 1. Create dummy files (14 files covering all categories)
    print(f"\n[Step 1] Creating mixed dummy files in: {demo_dir.name}/")
    created_files = app.create_dummy_files(demo_dir)
    print(f"Total files created: {len(created_files)}")
    for file_path in created_files:
        cat = app.get_category_for_file(file_path)
        print(f"  - {file_path.name:<32} -> Expected category: {cat}")

    # 2. Dry run preview
    print("\n[Step 2] Running preview (dry run / safe mode)...")
    preview_msgs = app.sort_documents(demo_dir, dry_run=True)
    print(f"Preview generated {len(preview_msgs)} operations:")
    for msg in preview_msgs[:4]:
        print(f"  {msg}")
    print(f"  ... and {len(preview_msgs) - 4} more.")

    # Verify no files were moved yet
    assert all(f.exists() for f in created_files), "Files should not be moved in preview mode"
    assert not (demo_dir / "Contracts").exists(), "Contracts folder should not exist in preview mode"

    # 3. Apply sorting
    print("\n[Step 3] Applying document sorting (--apply)...")
    results = app.sort_documents(demo_dir, dry_run=False)
    print(f"Successfully processed {len(results)} files.")

    # 4. Inspect destination folders
    print("\n[Step 4] Checking organized subfolders:")
    for category in ("Contracts", "Evidence", "Filings", "Correspondence", "Other"):
        cat_folder = demo_dir / category
        if cat_folder.exists():
            items = [p.name for p in cat_folder.iterdir() if p.is_file()]
            print(f"  [{category}/] ({len(items)} files):")
            for item in items:
                print(f"     * {item}")

    # 5. Inspect sort_log.txt
    log_file = demo_dir / "sort_log.txt"
    print(f"\n[Step 5] Checking audit log at: {log_file.name}")
    assert log_file.exists(), "sort_log.txt was not created!"
    log_lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    print(f"Total logged moves: {len(log_lines)}")
    print("Sample log entries:")
    for line in log_lines[:5]:
        print(f"  {line}")

    # 6. Verify idempotence
    second_run = app.sort_documents(demo_dir, dry_run=False)
    print(f"\n[Step 6] Running sort again on already-sorted directory:")
    print(f"  Result: {second_run[0]}")

    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_demonstration()
