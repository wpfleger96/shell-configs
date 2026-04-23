#!/usr/bin/env pwsh
param (
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Directory
)

if (-not (Test-Path -Path $Directory -PathType Container)) {
    Write-Error "Directory not found: $Directory"
    exit 1
}

function Process-File {
    param (
        [string]$filePath
    )

    $fileName = [System.IO.Path]::GetFileName($filePath)
    $fileExtension = [System.IO.Path]::GetExtension($filePath)

    if ($fileExtension -eq ".pdf" -or $fileExtension -eq ".png" -or $fileExtension -eq ".jpg") {
        if ($fileName -match "^(\d{1,2})-(\d{1,2})-(\d{1,2}) - (.+)\.([pdf|png|jpg]+)$") {
            $month = "{0:D2}" -f [int]$matches[1]
            $day = "{0:D2}" -f [int]$matches[2]
            $year = $matches[3]
            $name = $matches[4]
            $extension = $matches[5]

            $fullYear = "20$year"

            $newFileName = "$fullYear-$month-$day - $name.$extension"

            $directory = [System.IO.Path]::GetDirectoryName($filePath)

            $newFilePath = [System.IO.Path]::Combine($directory, $newFileName)

            $counter = 1

            while (Test-Path -Path $newFilePath) {
                $newFileName = "$fullYear-$month-$day - $name-$counter.$extension"
                $newFilePath = [System.IO.Path]::Combine($directory, $newFileName)
                $counter++
            }

            Rename-Item -Path $filePath -NewName $newFilePath

            Write-Output "Renamed: $fileName to $newFileName"
        } else {
            Write-Output "Skipped (no match): $fileName"
        }
    }
}

function Process-Directory {
    param (
        [string]$dirPath
    )

    Write-Host "Processing dir: $dirPath"

    $items = Get-ChildItem -Path $dirPath

    foreach ($item in $items) {
        if ($item.PSIsContainer) {
            Process-Directory -dirPath $item.FullName
        } else {
            Process-File -filePath $item.FullName
        }
    }
}

Process-Directory -dirPath (Resolve-Path $Directory).Path
