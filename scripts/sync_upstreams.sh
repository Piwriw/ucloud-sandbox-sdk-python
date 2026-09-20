#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_DIR="upstream"
E2B_SUBMODULE_PATH="$UPSTREAM_DIR/e2b"
E2B_PACKAGE_PATH="$E2B_SUBMODULE_PATH/packages/python-sdk/e2b"
CODE_INTERPRETER_PACKAGE_PATH="$E2B_SUBMODULE_PATH/packages/code-interpreter-python/e2b_code_interpreter"
DESKTOP_PACKAGE_PATH="$E2B_SUBMODULE_PATH/packages/desktop-python/e2b_desktop"
TARGET_PACKAGE_PATH="ucloud_sandbox"

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

TARGET_DIR="$REPO_ROOT/$TARGET_PACKAGE_PATH"

ensure_upstream_sources() {
  local needs_update=0
  local source_path

  if [ ! -e "$REPO_ROOT/$E2B_SUBMODULE_PATH/.git" ]; then
    needs_update=1
  fi

  for source_path in \
    "$E2B_PACKAGE_PATH" \
    "$CODE_INTERPRETER_PACKAGE_PATH" \
    "$DESKTOP_PACKAGE_PATH"; do
    if [ ! -d "$REPO_ROOT/$source_path" ]; then
      needs_update=1
    fi
  done

  if [ "$needs_update" -eq 1 ]; then
    echo "Initializing/updating upstream submodules"
    git submodule update --init --recursive "$E2B_SUBMODULE_PATH"
  fi
}

assert_source_dir() {
  local source_path="$1"

  if [ ! -d "$REPO_ROOT/$source_path" ]; then
    echo "Upstream source not found: $source_path" >&2
    exit 1
  fi
}

replace_dir() {
  local source_path="$1"
  local target_path="$2"
  local source_dir="$REPO_ROOT/$source_path"
  local target_dir="$REPO_ROOT/$target_path"

  if [ -L "$target_dir" ]; then
    echo "Refusing to replace symlink target: $target_path" >&2
    exit 1
  fi

  mkdir -p "$target_dir"

  echo "Replacing $target_path with $source_path"
  find "$target_dir" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
  cp -a "$source_dir"/. "$target_dir"/
}

ensure_upstream_sources
assert_source_dir "$E2B_PACKAGE_PATH"
assert_source_dir "$CODE_INTERPRETER_PACKAGE_PATH"
assert_source_dir "$DESKTOP_PACKAGE_PATH"

if [ -L "$TARGET_DIR" ]; then
  echo "Refusing to replace symlink target: $TARGET_PACKAGE_PATH" >&2
  exit 1
fi

replace_dir "$E2B_PACKAGE_PATH" "$TARGET_PACKAGE_PATH"
replace_dir "$CODE_INTERPRETER_PACKAGE_PATH" "$TARGET_PACKAGE_PATH/code_interpreter"
replace_dir "$DESKTOP_PACKAGE_PATH" "$TARGET_PACKAGE_PATH/desktop"

echo "Done."
