$log = "reports\final_validation_log.txt"
"Final validation run: $(Get-Date -Format s)" | Out-File $log -Encoding utf8
$steps = @(
  @("pytest", "python -m pytest -q"),
  @("python vs raw reconciliation", "python src\reconcile.py"),
  @("KPI check", "python -m src.kpis"),
  @("pandas vs SQL", "python -m src.check_db_connection")
)
$fail = 0
foreach ($s in $steps) {
  "=== $($s[0]) ===" | Tee-Object -FilePath $log -Append
  cmd /c "$($s[1]) 2>&1" | Tee-Object -FilePath $log -Append
  if ($LASTEXITCODE -ne 0) { $fail++; "FAILED: $($s[0])" | Tee-Object -FilePath $log -Append }
}
"Failed steps: $fail" | Tee-Object -FilePath $log -Append
exit $fail