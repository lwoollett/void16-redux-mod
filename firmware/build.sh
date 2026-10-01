#!/usr/bin/env bash
# Build void16-redux-mod firmware for nice!nano v2 (nRF52840).
# Zephyr 4.1's FindZephyr-sdk.cmake has an unquoted ${ZEPHYR_TOOLCHAIN_VARIANT} in if(),
# which hard-errors under CMake 4.x when unset. Setting it explicitly avoids the bug.
export ZEPHYR_TOOLCHAIN_VARIANT=zephyr
export PATH="/Users/luke/repos/zmk/.venv/bin:$PATH"
# Usage: ./build.sh [build-dir]   (default: build/void16)
set -euo pipefail

ZMK=/Users/luke/repos/zmk
CONFIG="$(cd "$(dirname "$0")" && pwd)/config"
BUILD_DIR=${1:-build/void16}

cd "$ZMK"
.venv/bin/west build -p -s app -d "$BUILD_DIR" -b 'nice_nano//zmk' -- \
  -DZMK_CONFIG="$CONFIG"

echo
echo "UF2: $ZMK/$BUILD_DIR/zephyr/zmk.uf2"

mkdir -p "$(dirname "$0")"
cp "$ZMK/$BUILD_DIR/zephyr/zmk.uf2" "$(dirname "$0")/staged-zmk.uf2.tmp"
mv -f "$(dirname "$0")/staged-zmk.uf2.tmp" "$(dirname "$0")/staged-zmk.uf2"
echo "Staged: $(dirname "$0")/staged-zmk.uf2"
