@"
# Dataset Source and License

- **Name:** Brazilian E-Commerce Public Dataset by Olist
- **Source:** Kaggle (dataset slug: olistbr/brazilian-ecommerce)
- **License:** CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/)
- **Terms in plain English:** attribution required; non-commercial use only; derivatives must use the same license.
- **Raw files:** stored in data/raw/, never modified, never committed to GitHub.
- **Integrity:** SHA-256 hashes recorded in reports/data_quality/raw_data_manifest.csv
- **Date downloaded:** $(Get-Date -Format yyyy-MM-dd)
- **Version note:** row counts in the manifest reflect the version I downloaded.
"@ | Set-Content -Encoding utf8 docs\dataset_source_and_license.md