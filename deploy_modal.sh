#!/bin/bash
# Deploy PAWS Modal Endpoint

echo "🚀 Deploying PAWS Vision Engine to Modal.com..."
echo ""

# Check if Modal is installed
if ! command -v modal &> /dev/null; then
    echo "❌ Modal CLI not found. Installing..."
    pip install modal
fi

# Check authentication
echo "🔐 Checking Modal authentication..."
modal token check || {
    echo "⚠️ Not authenticated. Opening browser..."
    modal token new
}

# Deploy to Modal
echo ""
echo "📦 Deploying modal_inference.py..."
cd "$(dirname "$0")/backend_fastapi"
modal deploy modal_inference.py

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "1. Copy the endpoint URL from above"
echo "2. Update MODAL_API_URL in backend_fastapi/main.py"
echo "3. Restart your backend server"
echo ""
echo "🎯 Test your deployment:"
echo "   modal logs paws-vision-engine"
echo ""
