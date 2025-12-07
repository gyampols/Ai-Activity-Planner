#!/bin/bash
# Script to properly encode Google Cloud service account key for CircleCI
# Usage: ./encode-service-account.sh path/to/service-account-key.json

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 path/to/service-account-key.json"
    exit 1
fi

SERVICE_ACCOUNT_FILE="$1"

if [ ! -f "$SERVICE_ACCOUNT_FILE" ]; then
    echo "Error: File '$SERVICE_ACCOUNT_FILE' not found!"
    exit 1
fi

echo "Encoding service account key..."
echo ""

# Validate JSON first
if ! python3 -m json.tool "$SERVICE_ACCOUNT_FILE" > /dev/null 2>&1; then
    echo "Error: Invalid JSON file!"
    exit 1
fi

echo "✓ JSON is valid"
echo ""

# Encode without newlines
ENCODED=$(cat "$SERVICE_ACCOUNT_FILE" | base64 | tr -d '\n')

# Save to file
echo "$ENCODED" > gcloud-service-key-encoded.txt

echo "✓ Service account key encoded successfully!"
echo ""
echo "Encoded key saved to: gcloud-service-key-encoded.txt"
echo ""
echo "The encoded key has also been copied to your clipboard (if pbcopy is available)"
echo ""

# Copy to clipboard if pbcopy is available
if command -v pbcopy &> /dev/null; then
    echo "$ENCODED" | pbcopy
    echo "✓ Copied to clipboard!"
else
    echo "⚠️  pbcopy not available. Copy from gcloud-service-key-encoded.txt manually"
fi

echo ""
echo "Next steps:"
echo "1. Go to CircleCI: https://app.circleci.com/"
echo "2. Organization Settings → Contexts → gcp-deployment"
echo "3. Remove the existing GCLOUD_SERVICE_KEY variable"
echo "4. Add it again with the newly encoded value"
echo "5. Make sure to paste the ENTIRE string (it's one long line with no breaks)"
echo ""
echo "⚠️  IMPORTANT: The encoded string should be ONE continuous line with NO spaces or newlines!"
