param([string]$Engine = '')
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    if (-not $Engine) {
        if (Get-Command xelatex -ErrorAction SilentlyContinue) { $Engine = 'xelatex' }
        elseif (Get-Command tectonic -ErrorAction SilentlyContinue) { $Engine = 'tectonic' }
        else { throw 'Install or select an existing XeLaTeX/Tectonic compiler; alternatively read main.pdf.' }
    }
    if ([IO.Path]::GetFileNameWithoutExtension($Engine) -eq 'tectonic') {
        & $Engine main.tex
        if ($LASTEXITCODE -ne 0) { throw 'Tectonic compilation failed.' }
    } else {
        1..2 | ForEach-Object {
            & $Engine -interaction=nonstopmode -halt-on-error main.tex
            if ($LASTEXITCODE -ne 0) { throw 'XeLaTeX compilation failed.' }
        }
    }
} finally { Pop-Location }
