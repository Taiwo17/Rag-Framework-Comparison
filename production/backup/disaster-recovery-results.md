# Disaster Recovery – Backup Results

## Objective

Create a recoverable backup of the FAISS vector store used by the production RAG API.

## Backup Implementation

- Backup script: `production/backup/backup.sh`
- Source: `evaluation/vector_stores/langchain/`
- Destination: `production/backup/`
- Backup naming: Timestamped directories (`faiss_YYYYMMDD_HHMMSS`)
- Integrity verification: SHA-256 checksums

## Backup Test

- Backup created successfully.
- Backup directory: `faiss_20261112_004934`
- `index.faiss`: SHA-256 verification passed.
- `index.pkl`: SHA-256 verification passed.

## Result

The FAISS vector store was copied successfully, and both backup files passed checksum verification.

## Limitations

- This test verifies backup creation and file integrity, not a complete restoration.
- Backups are currently stored on the same machine as the application.
- Off-site storage and automated backup scheduling are not yet implemented.

## Restoration Test

- Created an isolated restore-test directory.
- Copied `index.faiss` and `index.pkl` from the backup.
- Verified both files against the original SHA-256 checksums.
- Loaded the restored index using LangChain FAISS.
- Confirmed that all 20 indexed documents were available.
- The active production vector store was not modified.

## Restoration Result

Successful. The backup was verified and successfully loaded as a functional FAISS vector store.

## Backup Retention

- Configured the backup script to retain the five most recent timestamped backups.
- Older backups are automatically removed when the count exceeds five.
- Executed the updated backup script successfully.
- Confirmed that two timestamped backups currently exist.
- The restore-test directory is excluded from retention cleanup.

## Retention Test Limitation

The retention policy has been implemented and the backup script executed successfully. A test with more than five backups is still pending.

## Backup Retention Test

- Created six temporary test directories.
- Executed the retention cleanup logic.
- Confirmed that the oldest directory was removed.
- Verified that exactly five directories remained.
- Removed all temporary test directories afterward.
- Confirmed that actual FAISS backups were untouched.

## Retention Test Result

Passed. The retention cleanup logic correctly maintains a maximum of five timestamped backups.
