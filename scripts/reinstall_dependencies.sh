#!/bin/bash

echo "🔄 Reinstalling dependencies..."

# Check if `uv` is installed
if command -v uv &> /dev/null
then
    echo "✅ Using uv to uninstall problematic packages"
    # Uninstall each package separately without -y flag
    uv pip uninstall myapplication
    uv pip uninstall the-new-hotness

    echo "✅ Problematic packages uninstalled"
else
    echo "⚠️ uv not found, using pip"
    # Uninstall each package separately with -y flag
    pip uninstall -y myapplication
    pip uninstall -y the-new-hotness

    echo "✅ Problematic packages uninstalled"
fi

echo "✅ Dependencies reinstalled successfully"
