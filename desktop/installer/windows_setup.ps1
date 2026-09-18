param([Parameter(Mandatory=$true)][string]$InstallDir, [Parameter(Mandatory=$true)][string]$ManifestPath)
$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing, System.Net.Http, System.IO.Compression, System.IO.Compression.FileSystem
    # NSIS also extracts a native System.dll into its working directory.
    # Give the C# compiler actual managed assembly paths.
    $frameworkReferences = @(
        [System.Uri].Assembly.Location,
        [System.Linq.Enumerable].Assembly.Location,
        [System.Net.Http.HttpClient].Assembly.Location,
        [System.IO.Compression.ZipArchive].Assembly.Location,
        [System.IO.Compression.ZipFile].Assembly.Location
    )
    Add-Type -Path (Join-Path $PSScriptRoot 'windows_download.cs') -ReferencedAssemblies $frameworkReferences
    $spec = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($spec.version -ne '4.7.4' -or $spec.base_url -ne 'https://github.com/kimwoo666/shellground/releases/download/v4.7.4-preview/') { throw 'Unknown release' }
    function Part($record) {
        $part = New-Object ReleasePart
        $part.Name = $record.name; $part.Hash = $record.sha256; $part.Bytes = [long]$record.bytes
        return $part
    }
    [System.Windows.Forms.Application]::EnableVisualStyles()
    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'Shellground 설치'; $form.ClientSize = New-Object System.Drawing.Size(570,245)
    $form.StartPosition = 'CenterScreen'; $form.FormBorderStyle = 'FixedDialog'; $form.MaximizeBox = $false
    $heading = New-Object System.Windows.Forms.Label
    $heading.Text = 'Shellground'; $heading.Font = New-Object System.Drawing.Font('Segoe UI',22,[System.Drawing.FontStyle]::Bold)
    $heading.SetBounds(24,18,520,45); $form.Controls.Add($heading)
    $description = New-Object System.Windows.Forms.Label
    $description.Text = '실습 자료를 자동으로 준비합니다. 처음 설치할 때만 인터넷이 필요합니다.'
    $description.SetBounds(26,75,520,35); $form.Controls.Add($description)
    $status = New-Object System.Windows.Forms.Label; $status.SetBounds(26,116,520,35); $form.Controls.Add($status)
    $bar = New-Object System.Windows.Forms.ProgressBar; $bar.SetBounds(26,153,518,20); $form.Controls.Add($bar)
    $cancel = New-Object System.Windows.Forms.Button; $cancel.Text='취소'; $cancel.SetBounds(448,192,96,32); $form.Controls.Add($cancel)
    $job = New-Object ShellgroundSetup
    $cancel.Add_Click({ $job.Cancel(); $cancel.Enabled=$false; $status.Text='중단 중… 확인된 자료는 다음 설치에서 이어 받습니다.' })
    $form.Add_FormClosing({ param($sender,$eventArgs) if (-not $job.Finished) { $eventArgs.Cancel=$true; $job.Cancel(); $cancel.Enabled=$false } })
    $timer = New-Object System.Windows.Forms.Timer; $timer.Interval=200
    $timer.Add_Tick({
        $status.Text=$job.Stage
        if ($job.Total -gt 0) {
            $bar.Value=[Math]::Min(100,[Math]::Max(0,[int](100.0*$job.Current/$job.Total)))
            $status.Text += (' · {0:N2} / {1:N2} GB' -f ($job.Current/1e9),($job.Total/1e9))
        }
        if ($job.Finished) { $timer.Stop(); $form.Close() }
    })
    [ReleasePart[]]$parts = @($spec.disk.parts | ForEach-Object { Part $_ })
    $job.Start([IO.Path]::GetFullPath($InstallDir), (Part $spec.windows), $parts, $spec.disk.sha256, [long]$spec.disk.bytes)
    $timer.Start(); [void]$form.ShowDialog(); $timer.Dispose(); $form.Dispose()
    if (-not $job.Succeeded) { throw $job.Error }
    exit 0
} catch {
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Shellground 설치', 'OK', 'Error') | Out-Null
    exit 1
}
