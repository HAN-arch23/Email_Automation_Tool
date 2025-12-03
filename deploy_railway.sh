#!/bin/bash

# Email Automation Tool - Railway Deployment Script
# This script helps you deploy to Railway quickly

set -e

echo "🚂 Railway Deployment Helper"
echo "=============================="
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found!"
    echo "📦 Installing Railway CLI..."
    npm install -g @railway/cli
fi

# Check if logged in
echo "🔐 Checking Railway authentication..."
if ! railway whoami &> /dev/null; then
    echo "Please login to Railway:"
    railway login
fi

# Initialize project if not already done
if [ ! -f "railway.toml" ]; then
    echo "🆕 Initializing Railway project..."
    railway init
fi

# Add PostgreSQL if not already added
echo "🗄️  Setting up PostgreSQL database..."
railway add --database postgresql || echo "Database already exists"

# Set environment variables
echo ""
echo "🔑 Setting up environment variables..."
echo "Enter your SECRET_KEY (or press Enter to generate one):"
read -r SECRET_KEY

if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "Generated SECRET_KEY: $SECRET_KEY"
fi

railway variables set SECRET_KEY="$SECRET_KEY"

echo ""
echo "Enter DEFAULT_SENDER_EMAIL (optional, press Enter to skip):"
read -r DEFAULT_SENDER_EMAIL

if [ -n "$DEFAULT_SENDER_EMAIL" ]; then
    railway variables set DEFAULT_SENDER_EMAIL="$DEFAULT_SENDER_EMAIL"
fi

# Deploy
echo ""
echo "🚀 Deploying to Railway..."
railway up

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 View logs: railway logs"
echo "🌐 Get URL: railway domain"
echo "⚙️  Dashboard: https://railway.app/dashboard"
echo ""
