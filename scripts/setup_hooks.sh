#!/bin/bash
# Pre-commit Hook Setup Script (shared via repository-tracked .githooks)

echo "🔧 Configuring Git to use repository-tracked hooks (.githooks)..."

cat << 'EOF' > .githooks/pre-commit
#!/bin/sh
echo "🔍 Running MkDocs Strict Mode Validation before commit..."

export PATH="$HOME/.local/bin:$PATH"

MKDOCS_CMD=""

if command -v uv >/dev/null 2>&1; then
    MKDOCS_CMD="uv run mkdocs"
elif command -v mkdocs >/dev/null 2>&1; then
    MKDOCS_CMD="mkdocs"
elif [ -f ".venv/bin/mkdocs" ]; then
    MKDOCS_CMD=".venv/bin/mkdocs"
elif [ -f "venv/bin/mkdocs" ]; then
    MKDOCS_CMD="venv/bin/mkdocs"
fi

if [ -n "$MKDOCS_CMD" ]; then
    $MKDOCS_CMD build --strict
    if [ $? -ne 0 ]; then
        echo "❌ Git Commit Aborted: MkDocs strict build failed due to warnings or broken links."
        echo "💡 Fix the warnings above before committing."
        exit 1
    fi
    echo "✅ MkDocs strict validation passed."
else
    echo "ℹ️  MkDocs is not installed in local python environment. (CI will validate on push)"
fi

exit 0
EOF

chmod +x .githooks/pre-commit
git config core.hooksPath .githooks

echo "✅ Successfully configured Git hooksPath to .githooks/"
echo "💡 Pre-commit strict validation is now active using uv / mkdocs."
