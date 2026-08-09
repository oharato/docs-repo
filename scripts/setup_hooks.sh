#!/bin/bash
# Pre-commit Hook Setup Script

HOOK_FILE=".git/hooks/pre-commit"

echo "🔧 Setting up Git pre-commit hook..."

cat << 'EOF' > "$HOOK_FILE"
#!/bin/sh
echo "🔍 Running MkDocs Strict Mode Validation before commit..."

MKDOCS_CMD=""

if command -v mkdocs >/dev/null 2>&1; then
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

chmod +x "$HOOK_FILE"
echo "✅ Git pre-commit hook successfully installed at $HOOK_FILE"
