$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot
Push-Location $projectDirectory
try {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required.' }
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & .\.venv\Scripts\python.exe -m unittest test_real_lab.CurriculumTests -v
    if ($LASTEXITCODE -ne 0) { throw 'Curriculum tests failed.' }
    & .\.venv\Scripts\python.exe build.py
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
    Write-Host 'Output: desktop\dist\Shellground.exe'
    Write-Host 'Run Docker Desktop in Linux containers mode before opening a lab.'
} finally {
    Pop-Location
}
