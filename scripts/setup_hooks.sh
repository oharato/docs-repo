#!/bin/bash
# Pre-commit Hook Setup Script (shared via repository-tracked .githooks)

echo "🔧 Configuring Git to use repository-tracked hooks (.githooks)..."

chmod +x .githooks/pre-commit
git config core.hooksPath .githooks

echo "✅ Successfully configured Git hooksPath to .githooks/"
echo "💡 Pre-commit strict validation is now active for this repository."
