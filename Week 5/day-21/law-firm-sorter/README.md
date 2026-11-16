# Law Firm Document Sorter (Moi Avenue, Nairobi)

Automated legal document organizer built using safe, modular file automation patterns.

## Problem Scenario

A law firm located on Moi Avenue in Nairobi downloads client documents into a single intake folder throughout the day: scanned IDs, executed agreements, court filings, evidence photos, client correspondence, and receipts. By the end of each week, the folder accumulates hundreds of mixed files with arbitrary names (such as `scan001.pdf`, `IMG_4827.jpg`, and `Contract_FINAL_v3.docx`).

This tool automatically categorizes these documents into dedicated subfolders and generates a complete audit trail in `sort_log.txt`.

## Category Rules

| Category | Matching File Extensions | Typical Content |
| :--- | :--- | :--- |
| **Contracts/** | `.docx`, `.doc` | Commercial agreements, leases, employment contracts, deeds |
| **Evidence/** | `.jpg`, `.jpeg`, `.png` | Accident scene photos, scanned national IDs, passport copies |
| **Filings/** | `.pdf` | Court petitions, affidavits of service, pleadings, court orders |
| **Correspondence/** | `.txt`, `.eml` | Client conference notes, email threads, written instructions |
| **Other/** | All remaining extensions | Financial receipts (`.xlsx`), audio briefings (`.mp3`), archives (`.zip`) |

## Key Features

- **Safe By Default (Dry-Run Preview)**: Mutating commands only preview changes unless explicitly executed with `--apply`.
- **Audit Logging**: Appends a timestamped log of every move to `sort_log.txt` (or a custom `--log-file` path).
- **Collision Protection**: Validates all operations beforehand to prevent accidental file overwrites (`FileExistsError`).
- **Log and Subdirectory Protection**: Automatically avoids moving the active `sort_log.txt` or previously sorted category subdirectories.
- **Built-in Dummy Generator**: Quickly generate 14 realistic sample client files for testing.

## CLI Usage

### 1. Preview Sorting (Dry-Run Mode)
```bash
python app.py sort <path-to-folder>
```
*Outputs what files would be moved without modifying the filesystem.*

### 2. Apply Sorting
```bash
python app.py sort <path-to-folder> --apply
```
*Creates category folders as needed, moves the files, and appends records to `sort_log.txt`.*

### 3. Specify Custom Log Path
```bash
python app.py sort <path-to-folder> --apply --log-file path/to/audit.log
```

### 4. Create Dummy Test Files
```bash
python app.py create-dummy <path-to-folder>
```
*Populates the target folder with 14 mixed client files covering all 5 categories.*

### 5. Utility Commands
```bash
# List files in folder
python app.py list <path-to-folder>

# Check if path exists
python app.py exists <path>

# Create folder safely
python app.py mkdir <path-to-folder> --apply

# Copy or move individual files
python app.py copy <source> <destination> --apply
python app.py move <source> <destination> --apply
```

## Sample `sort_log.txt` Output

```text
[2026-11-16 19:02:49] C:\law_firm\intake\Accident_Scene_Photo_01.jpeg -> C:\law_firm\intake\Evidence\Accident_Scene_Photo_01.jpeg
[2026-11-16 19:02:49] C:\law_firm\intake\Affidavit_of_Service.pdf -> C:\law_firm\intake\Filings\Affidavit_of_Service.pdf
[2026-11-16 19:02:49] C:\law_firm\intake\Case_Evidence_Archive.zip -> C:\law_firm\intake\Other\Case_Evidence_Archive.zip
[2026-11-16 19:02:49] C:\law_firm\intake\Client_Consultation_Notes.txt -> C:\law_firm\intake\Correspondence\Client_Consultation_Notes.txt
[2026-11-16 19:02:49] C:\law_firm\intake\Commercial_Lease_Agreement.doc -> C:\law_firm\intake\Contracts\Commercial_Lease_Agreement.doc
[2026-11-16 19:02:49] C:\law_firm\intake\Contract_FINAL_v3.docx -> C:\law_firm\intake\Contracts\Contract_FINAL_v3.docx
[2026-11-16 19:02:49] C:\law_firm\intake\Court_Filing_Fee_Receipt.xlsx -> C:\law_firm\intake\Other\Court_Filing_Fee_Receipt.xlsx
[2026-11-16 19:02:49] C:\law_firm\intake\Employment_Contract_Signed.docx -> C:\law_firm\intake\Contracts\Employment_Contract_Signed.docx
[2026-11-16 19:02:49] C:\law_firm\intake\High_Court_Petition_2026.pdf -> C:\law_firm\intake\Filings\High_Court_Petition_2026.pdf
[2026-11-16 19:02:49] C:\law_firm\intake\IMG_4827.jpg -> C:\law_firm\intake\Evidence\IMG_4827.jpg
[2026-11-16 19:02:49] C:\law_firm\intake\Scanned_National_ID.png -> C:\law_firm\intake\Evidence\Scanned_National_ID.png
[2026-11-16 19:02:49] C:\law_firm\intake\Settlement_Offer_Thread.eml -> C:\law_firm\intake\Correspondence\Settlement_Offer_Thread.eml
[2026-11-16 19:02:49] C:\law_firm\intake\Witness_Interview_Audio.mp3 -> C:\law_firm\intake\Other\Witness_Interview_Audio.mp3
[2026-11-16 19:02:49] C:\law_firm\intake\scan001.pdf -> C:\law_firm\intake\Filings\scan001.pdf
```

## Running the Verification & Tests

### Automated Unit Tests
```bash
python -m unittest test_app.py
```

### End-to-End Demonstration Script
```bash
python run_test_demo.py
```
This script creates a dummy directory with 14 mixed files, tests safe dry-run preview, executes sorting with `--apply`, verifies each subfolder and the generated `sort_log.txt`, and confirms idempotence.
