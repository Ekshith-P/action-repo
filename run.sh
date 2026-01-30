#!/bin/bash
# Run the webhook-repo Flask app. Use from ASSIGNMENT/webhook-repo or ASSIGNMENT.

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo "Creating virtualenv..."
  python3 -m venv venv
fi

echo "Activating venv and installing dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

echo "Starting Flask app on http://localhost:5001"
echo "  UI: http://localhost:5001"
echo "  Webhook: http://localhost:5001/webhook"
echo "Press Ctrl+C to stop."
python app.py
