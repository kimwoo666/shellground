$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot
$fullValidation = $args -contains '--full-validation'
$buildArguments = @($args | Where-Object { $_ -ne '--full-validation' })
$previousPythonUtf8 = $env:PYTHONUTF8
Push-Location $projectDirectory
try {
    $env:PYTHONUTF8 = '1'
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required.' }
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt -r python-requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    $env:OPENBLAS_NUM_THREADS = '1'
    $env:OMP_NUM_THREADS = '1'
    if ($fullValidation) {
        & .\.venv\Scripts\python.exe -m unittest test_python_course test_python_grading test_python_quiz test_python_worker test_python_review_grading test_build_layout -v
        if ($LASTEXITCODE -ne 0) { throw 'Curriculum tests failed.' }
        $buildArguments += @('--verification', 'full')
    }
    # Default checks the newly built artifact only; completed courses are not rerun.
    & .\.venv\Scripts\python.exe build.py @buildArguments
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
    Write-Host 'The Windows candidate executable path and completed checks are shown by build.py above.'
    Write-Host 'Distribute the whole Shellground folder, not only Shellground.exe.'
    Write-Host 'Bundled Python: no separate Python or WSL installation required.'
    Write-Host 'Native VM lifecycle/CPU and user-profile checks must pass before declaring the Windows port complete.'
} finally {
    $env:PYTHONUTF8 = $previousPythonUtf8
    Pop-Location
}
