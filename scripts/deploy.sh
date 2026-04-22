#!/usr/bin/env bash
# deploy.sh — Build Hugo site and deploy to Netlify
# Usage: bash scripts/deploy.sh [optional commit message]
set -e

cd "$(dirname "$0")/.."

echo "🔨 Building Hugo site..."
hugo --quiet

echo "🚀 Deploying to Netlify..."
COMMIT_MSG="${1:-Auto-deploy $(date '+%Y-%m-%d %H:%M')}"

# Check if netlify CLI is available
if command -v netlify &>/dev/null; then
    netlify deploy --prod --dir=public
else
    echo "⚠️  Netlify CLI not found."
    echo "   Install: npm install -g netlify-cli"
    echo "   Then run: netlify deploy --prod --dir=public"
    echo ""
    echo "   Or push to GitHub and enable Netlify GitHub integration:"
    echo "   1. Push this folder to a GitHub repo"
    echo "   2. Go to https://app.netlify.com → Add new site → Import from Git"
    echo "   3. Set build command: hugo"
    echo "   4. Set publish directory: public"
fi
