#!/bin/bash

# Email Automation Tool - Fly.io Deployment Script
# This script helps you deploy to Fly.io quickly

set -e

echo "✈️  Fly.io Deployment Helper"
echo "=============================="
echo ""

# Check if Fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI not found!"
    echo "📦 Installing Fly CLI..."
    curl -L https://fly.io/install.sh | sh
    echo "⚠️  Please restart your terminal and run this script again"
    exit 1
fi

# Check if logged in
echo "🔐 Checking Fly.io authentication..."
if ! fly auth whoami &> /dev/null; then
    echo "Please login to Fly.io:"
    fly auth login
fi

# Launch app if not already done
if [ ! -f "fly.toml" ]; then
    echo "🆕 Launching Fly.io app..."
    fly launch --no-deploy
else
    echo "✅ fly.toml found, skipping launch"
fi

# Set environment variables
echo ""
echo "🔑 Setting up environment variables..."
echo "Enter your SECRET_KEY (or press Enter to generate one):"
read -r SECRET_KEY

if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "Generated SECRET_KEY: $SECRET_KEY"
fi

fly secrets set SECRET_KEY="$SECRET_KEY"

echo ""
echo "Enter DEFAULT_SENDER_EMAIL (optional, press Enter to skip):"
read -r DEFAULT_SENDER_EMAIL

if [ -n "$DEFAULT_SENDER_EMAIL" ]; then
    fly secrets set DEFAULT_SENDER_EMAIL="$DEFAULT_SENDER_EMAIL"
fi

# Deploy
echo ""
echo "🚀 Deploying to Fly.io..."
fly deploy

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 View logs: fly logs"
echo "🌐 Open app: fly open"
echo "⚙️  Dashboard: https://fly.io/dashboard"
echo ""
