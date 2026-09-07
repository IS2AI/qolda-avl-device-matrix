#!/usr/bin/env bash
# Device 3 (OnePlus 13R / Snapdragon 8 Gen 3, CPU) — build for Android and stage
# the device. Transcribed from summary.md "Exact commands run".
#
# Topology: this harness runs on a Mac and drives llama-server ON THE PHONE over
# wireless ADB. The phone is unplugged during measured runs, so the battery is
# discharging and BatteryManager reports a real draw.
#
# Requires: Android NDK in $NDK, cmake, ninja, adb, huggingface-cli (hf).
set -euo pipefail
cd "$(dirname "$0")"

COMMIT=ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31
PATCH="$(cd ../protocol && pwd)/qwen3avl-support.patch"
DEV_ROOT=/data/local/tmp/qolda
: "${NDK:?set NDK to your Android NDK root}"
: "${ADB_SERIAL:?set ADB_SERIAL, e.g. export ADB_SERIAL=<phone-ip>:5555}"

for c in cmake ninja adb hf; do
  command -v $c >/dev/null || { echo "FATAL: $c not found"; exit 1; }
done

# Host-side inputs: the driver base64s the media into HTTP requests from THIS
# directory. Only the smoke test reads them from the device.
cp ../protocol/prompts_text.txt ../protocol/bench_image.jpg \
   ../protocol/bench_audio_10s.wav ../protocol/bench_audio_30s.wav .

if [ ! -d llama.cpp ]; then
  git clone https://github.com/ggml-org/llama.cpp llama.cpp
fi
(
  cd llama.cpp
  git checkout "$COMMIT"
  git apply --check -v "$PATCH"
  git apply -v "$PATCH"
  # -march=armv8.2-a+dotprod+i8mm. i8mm is what makes Q4_K_M viable here; see
  # the quantization-scaling section of the cross-device report.
  cmake -B build-android -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$NDK/build/cmake/android.toolchain.cmake" \
    -DANDROID_ABI=arm64-v8a \
    -DANDROID_PLATFORM=android-28 \
    -DCMAKE_BUILD_TYPE=Release \
    -DGGML_NATIVE=OFF \
    -DGGML_CPU_ARM_ARCH=armv8.2-a+dotprod+i8mm \
    -DGGML_OPENMP=OFF \
    -DLLAMA_CURL=OFF \
    -DLLAMA_BUILD_TESTS=OFF \
    -DLLAMA_BUILD_EXAMPLES=OFF
  cmake --build build-android -j 10 \
    --target llama-server llama-mtmd-cli llama-tokenize
)

hf download issai/Qolda-AVL-5B-GGUF --local-dir models --exclude "imatrix/*"

adb -s "$ADB_SERIAL" shell "mkdir -p $DEV_ROOT/bin $DEV_ROOT/models $DEV_ROOT/art $DEV_ROOT/logs"
adb -s "$ADB_SERIAL" push llama.cpp/build-android/bin/. "$DEV_ROOT/bin/"
adb -s "$ADB_SERIAL" push models/. "$DEV_ROOT/models/"
adb -s "$ADB_SERIAL" push bench_image.jpg bench_audio_10s.wav bench_audio_30s.wav \
                          prompts_text.txt "$DEV_ROOT/art/"
adb -s "$ADB_SERIAL" shell "chmod +x $DEV_ROOT/bin/*"

echo "OK. Next: audio smoke test, then ./run.sh"
echo "  adb -s $ADB_SERIAL shell 'cd $DEV_ROOT && LD_LIBRARY_PATH=bin bin/llama-mtmd-cli \\"
echo "    -m models/Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf \\"
echo "    --mmproj models/mmproj/mmproj-Qolda-AVL-5B-F16.gguf \\"
echo "    --audio art/bench_audio_30s.wav -t 6 -n 32 --no-mmap \\"
echo "    -p \"Аудиодағы сөйлеуді сөзбе-сөз жазып шық.\"'"
