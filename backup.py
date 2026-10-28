from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import boto3


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup(source: Path, bucket: str, prefix: str) -> str:
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"Source directory does not exist: {source}")
    s3 = boto3.client("s3")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with tempfile.TemporaryDirectory(prefix="cloud-backup-") as temp_dir:
        archive = Path(temp_dir) / "backup.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
            for path in sorted(source.rglob("*")):
                if path.is_file() and not path.is_symlink():
                    zipped.write(path, arcname=Path(source.name) / path.relative_to(source))
        checksum = digest_file(archive)
        key = f"{prefix.strip('/')}/{source.name}/{timestamp}-{checksum[:12]}.zip"
        s3.upload_file(
            str(archive), bucket, key,
            ExtraArgs={"ServerSideEncryption": "AES256", "Metadata": {"sha256": checksum}},
        )
    print(f"Uploaded s3://{bucket}/{key}")
    print(f"SHA-256: {checksum}")
    return key


def restore(bucket: str, key: str, destination: Path) -> None:
    destination = destination.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cloud-restore-") as temp_dir:
        archive = Path(temp_dir) / "backup.zip"
        boto3.client("s3").download_file(bucket, key, str(archive))
        with zipfile.ZipFile(archive) as zipped:
            for member in zipped.infolist():
                target = (destination / member.filename).resolve()
                if target != destination and destination not in target.parents:
                    raise ValueError("Archive contains an unsafe path")
                mode = member.external_attr >> 16
                if mode & 0o170000 == 0o120000:
                    raise ValueError("Archive contains a symbolic link")
            zipped.extractall(destination)
    print(f"Restored to {destination}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up and restore a directory using Amazon S3.")
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("backup", help="Zip a directory and upload it to S3.")
    make.add_argument("source", type=Path)
    make.add_argument("--bucket", required=True)
    make.add_argument("--prefix", default="backups")
    recover = commands.add_parser("restore", help="Download and safely extract a backup.")
    recover.add_argument("--bucket", required=True)
    recover.add_argument("--key", required=True)
    recover.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "backup":
        backup(args.source, args.bucket, args.prefix)
    else:
        restore(args.bucket, args.key, args.destination)


if __name__ == "__main__":
    main()
