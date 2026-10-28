# S3 Cloud Backup CLI

A Python command-line tool that creates timestamped ZIP backups, calculates a SHA-256 checksum, encrypts uploads with S3-managed encryption, and restores archives with path-traversal checks. Terraform provisions a private, versioned S3 bucket with a configurable retention lifecycle.

## Provision storage

Prerequisites: AWS CLI credentials and Terraform 1.6+.

```bash
cd infra
terraform init
terraform apply
terraform output -raw bucket_name
```

Install the Python dependency from the project root with `python -m pip install -r requirements.txt`.

## Create and restore a backup

```bash
python backup.py backup ./my-folder --bucket YOUR_BUCKET
python backup.py restore --bucket YOUR_BUCKET --key backups/my-folder/TIMESTAMP-CHECKSUM.zip --destination ./restored
```

The backup command prints the exact object key and checksum. Use that key for restore. AWS credentials come from the standard AWS credential chain; no keys belong in source files.

## Retention and security

The bucket blocks public access, enables versioning and server-side encryption, and expires current backup objects after 90 days by default. Override with `-var=retention_days=180` when applying Terraform. Lifecycle expiry may take time to process. Backups can include sensitive data; restrict IAM access and never share the bucket publicly.

## Remove resources

Back up or intentionally delete objects and versions first. Then run `terraform destroy` from `infra/`. Terraform does not force-delete backup data.
