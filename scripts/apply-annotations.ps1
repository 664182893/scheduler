# 把 scripts/annotations/ 里的中文注释映射应用到源码树。
# 用法: powershell -File scripts/apply-annotations.ps1 [-SourceRoot DIR] [-Only SUBSTR]
param(
    [string]$SourceRoot = "",
    [string]$Only = ""
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$arguments = @("$repo/scripts/apply_annotations.py")
if ($SourceRoot) { $arguments += @("--source-root", $SourceRoot) }
if ($Only) { $arguments += @("--only", $Only) }
python @arguments
exit $LASTEXITCODE
