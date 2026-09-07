# Device 1 (Windows / RTX 4090 Laptop, CUDA) - run the benchmark matrix.
#
# Power boundary here is GPU package only (nvidia-smi power.draw). CPU package
# power is NOT captured: no HWiNFO64 or LibreHardwareMonitor was installed, so
# real wall power is higher than the reported figure.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    throw "nvidia-smi not found; VRAM and power sampling both depend on it"
}
foreach ($f in @("prompts_text.txt","bench_image.jpg","bench_audio_10s.wav",
                 "bench_audio_30s.wav","models")) {
    if (-not (Test-Path $f)) { throw "missing $f - run .\setup.ps1 first" }
}
if (-not (Test-Path "C:\qolda-bench\llama.cpp\build\bin\Release\llama-server.exe")) {
    throw "llama-server.exe not at the path bench.py expects (see LLAMA_SERVER, line 17)"
}

# High-performance power plan. `-duplicatescheme` prints a NEW machine-specific
# GUID; the one below is what this machine produced. Run the duplicate command,
# read the GUID it prints, and set that one active.
#   powercfg -duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
#   powercfg -setactive <the GUID it printed>
powercfg -setactive fa079c95-1f81-45db-b272-0ab8f6883009

# Writes results.csv directly; there is no separate aggregation step on this device.
python bench.py
Write-Host "OK -> results.csv"
