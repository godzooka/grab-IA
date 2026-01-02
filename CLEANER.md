# grab-IA Directory Cleaner

A standalone tool for ensuring 1:1 parity between your item lists and download directories. The cleaner removes orphaned files, stray `.part` files, and unwanted formats while preserving exactly what should exist according to your Internet Archive manifests.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)

## Overview

The Directory Cleaner is a safety-focused tool that:
- **Fetches manifests** from Internet Archive for verification
- **Identifies orphaned files** that don't belong in your download directory
- **Respects all filters** (extensions, regex, metadata-only mode)
- **Provides dry-run mode** for safe preview before deletion
- **Ensures 1:1 parity** between your item list and local files

## When to Use the Cleaner

### Common Scenarios

**Scenario 1: Changing File Format Preferences**
```
You downloaded an entire collection, but now only want MP3 files.
→ Set extension filter to "mp3" and run cleaner to remove other formats.
```

**Scenario 2: Removing Partial Downloads**
```
Downloads were interrupted, leaving .part files everywhere.
→ Run cleaner to remove all .part files and orphaned items.
```

**Scenario 3: Collection Maintenance**
```
You modified your item list to exclude certain items.
→ Run cleaner to remove files from excluded items.
```

**Scenario 4: Filter Migration**
```
You initially downloaded without filters, now want only specific files.
→ Apply filters in cleaner to remove unwanted files.
```

## Installation

### Prerequisites
- Python 3.8 or higher
- Internet connection (to fetch manifests)
- Existing grab-IA installation

### Quick Start

```bash
# Launch the cleaner
python grabia_cleaner.py
```

The cleaner uses the same virtual environment as the main grab-IA application, so no additional installation is required.

## Usage Guide

### Basic Workflow

1. **Select Item List**: Browse for the same TXT/CSV file used for downloads
2. **Select Download Directory**: Point to your existing download folder
3. **Configure Filters** (optional): Apply the same filters you want to enforce
4. **Enable Dry-Run**: Preview changes without deleting anything
5. **Review Changes**: Examine the log to see what would be deleted
6. **Execute**: Uncheck dry-run and run again to perform actual deletion

### Interface Overview

#### Left Sidebar (Configuration)

| Field | Description |
|-------|-------------|
| **Item list** | TXT or CSV file with Archive.org identifiers |
| **Download directory** | Path to your grab-IA downloads folder |
| **Filename regex** | Regular expression to filter filenames |
| **Extensions** | Comma-separated list (e.g., `mp3,flac,pdf`) |
| **Metadata only** | Only keep XML, JSON, TXT files |
| **Keep README files** | Preserve grab-IA generated READMEs |
| **Dry-run mode** | Preview changes without deletion |

#### Right Panel (Activity Log)

Color-coded log showing:
- 🟢 **Green**: Successful operations
- 🟡 **Yellow**: Warnings and dry-run results
- 🔴 **Red**: Errors
- ⚪ **White**: Informational messages

## Features in Detail

### Dry-Run Mode (Recommended First Step)

**Always start with dry-run enabled** to preview changes safely.

```
Example Dry-Run Output:
═══════════════════════════════════════════════════════════════
🔍 DRY-RUN MODE - No files will be deleted
═══════════════════════════════════════════════════════════════

📋 Files that WOULD BE DELETED (15):
  - item_123/audio.flac
  - item_123/video.mp4
  - item_456/document.pdf.part
  - item_789/archive_meta.sqlite
  ...

📋 Missing files (not in local directory) (3):
  - item_123/cover.jpg
  - item_456/metadata.xml
  ...

✓ Dry-run complete. Enable 'Execute Cleaning' to make changes.
```

### Filter Compatibility

The cleaner respects **all the same filters** as the main downloader:

#### Extension Whitelist
```
Input: mp3,flac
Result: Only MP3 and FLAC files are kept, everything else is deleted
```

#### Regex Filtering
```
Input: .*live.*\.mp3$
Result: Only MP3 files with "live" in the name are kept
```

#### Metadata-Only Mode
```
Enabled: Only XML, JSON, TXT, and README files are kept
Result: All media files are deleted
```

#### Anti-Clutter (Always Active)
Automatically excludes Internet Archive system files:
- `_meta.xml`
- `_meta.sqlite`
- `_files.xml`
- `_thumb.jpg`
- `_itemimage.jpg`

### README Preservation

**Keep README files** (default: enabled)

When enabled, grab-IA generated `README.txt` files are preserved even if they're not in the Internet Archive manifest. These files contain valuable metadata about each item.

Disable this option if you want a pure 1:1 match with Internet Archive content only.

### Safety Features

#### Confirmation Dialog
When dry-run is disabled, you must confirm deletion:
```
⚠️  This will permanently DELETE files not in the manifest.
Are you sure you want to proceed?
```

#### Stop Button
Interrupt cleaning operation at any time with the STOP button.

#### Detailed Logging
Every action is logged with timestamps and file paths for audit trail.

## Usage Examples

### Example 1: Remove All Non-MP3 Files

**Goal**: You have a music collection with mixed formats, want only MP3s.

```
1. Item list: music_items.txt
2. Download directory: /downloads
3. Extensions: mp3
4. Dry-run: ✓ (enabled)
5. Click START CLEANING
6. Review log - shows FLAC, M4A, etc. would be deleted
7. Uncheck dry-run
8. Click START CLEANING again
9. Only MP3 files remain
```

### Example 2: Clean Up Interrupted Downloads

**Goal**: Remove `.part` files and incomplete items.

```
1. Item list: all_items.txt
2. Download directory: /downloads
3. No filters needed
4. Dry-run: ✓ (enabled)
5. Click START CLEANING
6. Review log - shows orphaned .part files
7. Uncheck dry-run
8. Click START CLEANING again
9. All .part files removed
```

### Example 3: Enforce Regex Pattern

**Goal**: Only keep files matching a specific pattern.

```
1. Item list: podcast_items.txt
2. Download directory: /downloads
3. Filename regex: episode_\d{3}\.mp3$
4. Dry-run: ✓ (enabled)
5. Click START CLEANING
6. Review log - shows non-matching files
7. Uncheck dry-run
8. Click START CLEANING again
9. Only episode_XXX.mp3 files remain
```

### Example 4: Metadata-Only Collection

**Goal**: Remove all media, keep only metadata files.

```
1. Item list: research_items.txt
2. Download directory: /downloads
3. Metadata only: ✓ (enabled)
4. Keep README files: ✓ (enabled)
5. Dry-run: ✓ (enabled)
6. Click START CLEANING
7. Review - shows all MP3, MP4, PDF would be deleted
8. Uncheck dry-run
9. Click START CLEANING again
10. Only XML, JSON, TXT, README remain
```

### Example 5: Remove Excluded Items

**Goal**: You updated item list to exclude certain items, need to clean them out.

```
1. Old list: 100 items
2. New list: 80 items (20 removed)
3. Item list: updated_items.txt (80 items)
4. Download directory: /downloads (contains all 100)
5. Dry-run: ✓ (enabled)
6. Click START CLEANING
7. Review - shows 20 item directories would be deleted
8. Uncheck dry-run
9. Click START CLEANING again
10. Only 80 items remain
```

## What Gets Deleted

The cleaner removes:

### ✅ Always Deleted
- `.part` files (incomplete downloads)
- Files not in Internet Archive manifest
- Entire item directories not in your item list
- Files that don't match your filter criteria

### ⚠️ Conditionally Deleted
- README files (only if "Keep README files" is disabled)
- Metadata files (if using format filters or regex that exclude them)

### ❌ Never Deleted
- Files that exactly match the Internet Archive manifest
- Files that pass all your filter criteria
- README files (when "Keep README files" is enabled)

## Output and Reporting

### Completion Summary

```
Cleaning complete!

Files deleted: 47 items
Files kept: 1,234 files
Missing files: 12
```

### Missing Files Report

The cleaner reports files that **should exist** but are missing locally:
```
📋 Missing files (not in local directory) (12):
  - item_123/track_05.mp3
  - item_456/document.pdf
  ...
```

This helps identify incomplete downloads that need to be re-downloaded with the main grab-IA tool.

## Integration with Main Downloader

### Workflow

```
1. Download collection with grab-IA
   → Items downloaded with all files
   
2. Decide you only want certain formats
   → Run cleaner with format filter
   
3. Continue downloading new items
   → Main downloader respects same filters
   
4. Periodic cleanup
   → Run cleaner to remove strays
```

### Shared Configuration

The cleaner uses the **same filter syntax** as the main downloader, ensuring consistency:

| Feature | Main Downloader | Cleaner |
|---------|----------------|---------|
| Extension whitelist | ✓ Downloads only | ✓ Keeps only |
| Regex filtering | ✓ Downloads matching | ✓ Keeps matching |
| Metadata-only | ✓ Downloads metadata | ✓ Keeps metadata |
| Anti-clutter | ✓ Skips system files | ✓ Removes system files |

## Best Practices

### 1. Always Start with Dry-Run
Never run the cleaner without first doing a dry-run preview.

### 2. Backup Important Data
Before first use, backup your download directory or test on a copy.

### 3. Review Logs Carefully
Read the complete log output to understand what will be deleted.

### 4. Use Specific Filters
Be explicit with extensions and regex patterns to avoid accidents.

### 5. Keep READMEs Enabled
Unless you have a specific reason, preserve README files for reference.

### 6. Regular Maintenance
Run the cleaner periodically to remove accumulated strays and `.part` files.

### 7. Verify Item List
Ensure your item list is current before running the cleaner.

## Safety and Recovery

### What If I Delete Something by Mistake?

**Option 1: Re-download**
```bash
# Use the main downloader to re-download deleted items
python grabia_cli.py resume --output /downloads
```

**Option 2: Restore from Backup**
If you backed up before cleaning, restore from backup.

**Option 3: Download Specific Items**
Create a new item list with just the needed items and download again.

### What If Cleaner Crashes?

The cleaner is **stateless** - it doesn't maintain a database. You can simply run it again. Operations are not transactional, so partial deletion may occur. Always use dry-run first.

## Performance

### Large Collections

For collections with thousands of files:
- **Manifest fetching**: ~2-5 seconds per item
- **Local scanning**: ~1 second per 1,000 files
- **Deletion**: ~100 files per second

### Network Requirements

The cleaner needs internet access to fetch manifests from Internet Archive. Allow ~1MB bandwidth per 100 items for metadata.

## Troubleshooting

### Issue: "Metadata fetch failed"
```
Cause: Internet Archive is unreachable or item doesn't exist
Solution: Check internet connection, verify item IDs
```

### Issue: "Failed to delete file"
```
Cause: File is locked, permission denied, or in use
Solution: Close programs using files, check permissions
```

### Issue: Too many files listed for deletion
```
Cause: Wrong item list or directory selected
Solution: Verify paths, use dry-run, double-check item list
```

### Issue: Missing files reported
```
Cause: Incomplete downloads or items not yet downloaded
Solution: Use main grab-IA to download missing files
```

### Issue: README files being deleted
```
Cause: "Keep README files" option is disabled
Solution: Enable the option before running
```

## Command-Line Alternative

While the cleaner is GUI-focused, you can script similar operations:

```bash
# Get list of expected files
for item in $(cat items.txt); do
    curl -s "https://archive.org/metadata/$item" | \
    jq -r '.files[].name' >> expected.txt
done

# Compare with local files
find downloads/ -type f > local.txt
comm -13 <(sort expected.txt) <(sort local.txt) > orphans.txt

# Review and delete
cat orphans.txt  # Review first!
# xargs -a orphans.txt rm  # Delete (careful!)
```

## Technical Details

### Manifest Validation

The cleaner fetches metadata from:
```
https://archive.org/metadata/{identifier}
```

And extracts the file list from the `files` array in the JSON response.

### Filter Application Order

1. **Anti-clutter filter** (remove system files)
2. **Extension whitelist** (if specified)
3. **Regex filter** (if specified)
4. **Metadata-only mode** (if enabled)

### Filename Sanitization

Filenames are sanitized using the same rules as the main downloader:
```python
safe_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
```

## FAQ

**Q: Will this delete my downloaded media files?**
A: Only if they don't match your filters. Always use dry-run first.

**Q: Can I undo a cleaning operation?**
A: No. Use dry-run mode and verify before executing.

**Q: Does this work with partially downloaded items?**
A: Yes. It removes `.part` files and incomplete items.

**Q: Can I run this on a shared network drive?**
A: Yes, but ensure you have write permissions.

**Q: How long does cleaning take?**
A: Depends on collection size. Fetching manifests is the slowest part (~2-5s per item).

**Q: Will this affect my grabia_state.db database?**
A: No. The cleaner is independent and doesn't modify the main database.

**Q: Can I clean while downloading?**
A: Not recommended. Stop downloads first to avoid conflicts.

**Q: What's the difference between sync mode and cleaner?**
A: Sync mode skips existing files during download. Cleaner removes files after download.

## Contributing

Improvements welcome! The cleaner is designed to be:
- **Conservative**: Defaults to dry-run
- **Transparent**: Logs every decision
- **Compatible**: Matches main downloader filters exactly

## Support

- **Issues**: GitHub Issues
- **Documentation**: This file
- **Logs**: Check the Activity Log in GUI

---

**Directory Cleaner** - Keep your archives clean and organized. 🧹
