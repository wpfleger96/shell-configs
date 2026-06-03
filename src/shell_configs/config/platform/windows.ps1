# Windows-Specific PowerShell Configuration

### Windows PATH additions ###
if (Test-Path "$env:LOCALAPPDATA\Programs\Microsoft VS Code\bin") {
    $env:PATH += ";$env:LOCALAPPDATA\Programs\Microsoft VS Code\bin"
}

### Windows Utilities ###
function which { param([string]$cmd) Get-Command $cmd -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source }
function touch { param([string]$path) if (Test-Path $path) { (Get-Item $path).LastWriteTime = Get-Date } else { New-Item $path -ItemType File | Out-Null } }
