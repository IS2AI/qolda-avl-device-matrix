# Device 1 (Windows / RTX 4090 Laptop, CUDA) - build llama.cpp and fetch models.
# PowerShell, not bash: this device ran on Windows and bench.py resolves
# llama-server.exe through a Windows path.
# Transcribed from summary.md "Exact commands run".
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$COMMIT = "ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31"
$PATCH  = (Resolve-Path "..\protocol\qwen3avl-support.patch").Path

# bench.py hardcodes this path (LLAMA_SERVER, line 17). Deviation #1 in
# summary.md: the working set was relocated to C:\qolda-bench because building
# under a OneDrive-synced folder broke nvcc's compiler-ID step. Keep it, or edit
# bench.py to match wherever you build.
$ROOT = "C:\qolda-bench"
New-Item -ItemType Directory -Force -Path $ROOT | Out-Null

# The driver reads the fixed inputs from its own directory.
Copy-Item ..\protocol\prompts_text.txt, ..\protocol\bench_image.jpg,
          ..\protocol\bench_audio_10s.wav, ..\protocol\bench_audio_30s.wav . -Force

Push-Location $ROOT
if (-not (Test-Path llama.cpp)) {
    git clone https://github.com/ggml-org/llama.cpp llama.cpp
}
Set-Location llama.cpp
git checkout $COMMIT
git apply --check -v $PATCH
git apply -v $PATCH

# CUDA toolset pinned to 12.6 and the arch set explicitly (Deviation #2):
# the system also had CUDA 13.1, which cmake selected by default, and its
# CMAKE_CUDA_ARCHITECTURES=native probe failed under driver 572.16.
# 89 = Ada Lovelace (RTX 4090).
cmake -B build -G "Visual Studio 17 2022" -T cuda=12.6 -DGGML_CUDA=ON `
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89
cmake --build build -j --config Release `
  --target llama-server llama-mtmd-cli llama-tokenize
Pop-Location

# Xet transfer disabled (Deviation #3).
$env:HF_HUB_DISABLE_XET = "1"
hf download issai/Qolda-AVL-5B-GGUF `
  BF16/Qolda-AVL-5B-BF16.gguf Q8_0/Qolda-AVL-5B-Q8_0.gguf `
  Q6_K/Qolda-AVL-5B-Q6_K.gguf Q5_K_M/Qolda-AVL-5B-Q5_K_M.gguf `
  Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf `
  mmproj/mmproj-Qolda-AVL-5B-F16.gguf `
  mmproj/mmproj-Qolda-AVL-5B-vision-only-F16.gguf `
  --local-dir models

python -m pip install psutil requests
Write-Host "OK. Next: .\run.ps1"
