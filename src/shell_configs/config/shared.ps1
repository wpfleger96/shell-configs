# Shared PowerShell Configuration

### Environment ###
$env:EDITOR = "vim"
$env:VISUAL = "vim"
$env:PAGER = "less"

### Git - Aliases ###
Remove-Alias -Name gc -Force -ErrorAction SilentlyContinue
Remove-Alias -Name gp -Force -ErrorAction SilentlyContinue
Remove-Alias -Name gl -Force -ErrorAction SilentlyContinue
function ga { git add @args }
function gaa { git add . }
function gc { git commit @args }
function gd { git diff @args }
function gds { git diff --staged @args }
function gl { git log --graph --decorate --max-count 15 --pretty=format:"%C(yellow)%h%Creset %C(green)%ad%Creset [%C(bold blue)%an%Creset] | %s%C(bold red)%d%Creset" --date=short }
function gf { git fetch @args }
function gp { git pull @args }
function gpu { git push @args }
function gs { git status @args }
function gst { git stash @args }

### Navigation ###
function .. { Set-Location .. }
function ... { Set-Location ../.. }

### Utilities ###
function mkcd { param([string]$dir) New-Item -ItemType Directory -Path $dir -Force | Out-Null; Set-Location $dir }
