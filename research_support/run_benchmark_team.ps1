param(
    [string]$Model = "deepseek-chat",
    [int]$Runs = 3,
    [double]$Temperature = 0.1,
    [string]$Repo = "django/django",
    [int]$Tasks = 50,
    [switch]$PrepareOnly
)

$ErrorActionPreference = "Stop"
# PowerShell 7+: do not fail on native stderr warnings (HF download messages, etc.).
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$VenvScripts = Join-Path $Root ".venv\Scripts"

# Avoid Windows cp1252 encoding crashes in benchmark scripts (Unicode arrows, etc.).
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONWARNINGS = "ignore"
if (Test-Path $VenvScripts) {
    $env:PATH = "$VenvScripts;$env:PATH"
}

if (-not (Test-Path $Python)) {
    Write-Error "Python venv not found: $Python`nCreate it with: python -m venv .venv"
}

function Invoke-PythonStep {
    param(
        [string[]]$ScriptArgs,
        [string]$LogFile,
        [string]$StepName
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Python
    $psi.Arguments = (($ScriptArgs | ForEach-Object { [string]$_ }) -join " ")
    $psi.WorkingDirectory = $Root
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    $proc = [System.Diagnostics.Process]::Start($psi)
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()

    $combined = ($stdout + $stderr).TrimEnd()
    if ($combined.Length -gt 0) {
        $combined | Tee-Object -FilePath $LogFile
    } else {
        "" | Out-File -FilePath $LogFile -Encoding utf8
    }

    if ($proc.ExitCode -ne 0) {
        throw "$StepName failed with exit code $($proc.ExitCode)"
    }
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogDir = Join-Path $Root "research_support\logs\$Timestamp"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Host "== CodeDNA Research Runner =="
Write-Host "Root: $Root"
Write-Host "Model: $Model | Runs: $Runs | Temp: $Temperature"
Write-Host "Repo: $Repo | Tasks: $Tasks"
Write-Host "Logs: $LogDir"

$SetupArgs = @(
    "labs/benchmark/setup_benchmark.py",
    "--repo", $Repo,
    "--n-tasks", $Tasks,
    "--multi-file-first"
)

Write-Host "`n[1/3] Preparing benchmark tasks..."
Invoke-PythonStep -ScriptArgs $SetupArgs -LogFile (Join-Path $LogDir "01_setup.txt") -StepName "Setup"

$AnnotateArgs = @(
    "labs/benchmark/setup_benchmark.py",
    "--repo", $Repo,
    "--n-tasks", $Tasks,
    "--multi-file-first",
    "--annotate",
    "--no-llm"
)

Write-Host "`n[2/3] Creating CodeDNA annotated variant (--no-llm)..."
Invoke-PythonStep -ScriptArgs $AnnotateArgs -LogFile (Join-Path $LogDir "02_annotate.txt") -StepName "Annotate"

if ($PrepareOnly) {
    Write-Host "`nPrepareOnly enabled. Stop before benchmark runs."
    exit 0
}

$RunArgs = @(
    "benchmark_agent/swebench/run_agent_multi.py",
    "--model", $Model,
    "--runs", $Runs,
    "--temperature", $Temperature,
    "--projects-dir", "labs/benchmark/projects",
    "--tasks-file", "labs/benchmark/tasks.json"
)

Write-Host "`n[3/3] Running benchmark..."
Invoke-PythonStep -ScriptArgs $RunArgs -LogFile (Join-Path $LogDir "03_run.txt") -StepName "Benchmark run"

Write-Host "`nDone. Next step:"
Write-Host "python benchmark_agent/swebench/analyze_multi.py"
Write-Host "python benchmark_agent/swebench/analyze_multi.py --qualitative"
