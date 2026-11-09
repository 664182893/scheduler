# 拉取 kube-scheduler v1.32.0 源码（tag zip，约 40MB，不含 .git）
param(
    [string]$Dest = "kubernetes-v1.32.0"
)

$ErrorActionPreference = "Stop"
$Version = "v1.32.0"

if (Test-Path "$Dest/pkg/scheduler/schedule_one.go") {
    Write-Host "source already present: $Dest"
    exit 0
}

$Url = "https://github.com/kubernetes/kubernetes/archive/refs/tags/$Version.zip"
$Zip = "$Dest.zip"

Write-Host "downloading $Url"
Invoke-WebRequest -Uri $Url -OutFile $Zip

if (Test-Path $Dest) {
    Remove-Item -Recurse -Force $Dest
}
Expand-Archive -Path $Zip -DestinationPath $Dest
Remove-Item $Zip

# GitHub 的 zip 解压后会多一层 kubernetes-<version> 目录
$Inner = Get-ChildItem $Dest -Directory | Select-Object -First 1
if ($Inner -and (Test-Path (Join-Path $Inner.FullName "pkg/scheduler/schedule_one.go"))) {
    Get-ChildItem $Inner.FullName -Force | Move-Item -Destination $Dest
    Remove-Item -Recurse -Force $Inner.FullName
}

if (-not (Test-Path "$Dest/pkg/scheduler/schedule_one.go")) {
    throw "unexpected layout: $Dest/pkg/scheduler/schedule_one.go not found"
}

Write-Host "done: $Dest"
Write-Host "verify: Get-Content $Dest/pkg/scheduler/schedule_one.go | Select-Object -Index 64"
