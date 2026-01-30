# webhook-repo

Flask webhook endpoint that receives GitHub events (Push, Pull Request, Merge) from **action-repo**, stores them in MongoDB, and serves a UI that polls every 15 seconds.

## Requirements

- Python 3.8+
- MongoDB (local or Atlas)

## Setup

1. Create a virtualenv and install dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Configure environment (optional):

   ```bash
   cp .env.example .env
   # Edit .env: MONGODB_URI, MONGODB_DB, PORT
   ```

3. Run MongoDB (if local):

   ```bash
   mongod
   ```

4. Start the Flask app:

   ```bash
   python app.py
   ```

   UI: http://localhost:5000  
   Webhook URL for GitHub: http://your-host:5000/webhook

## GitHub webhook setup (action-repo)

In **action-repo** → Settings → Webhooks → Add webhook:

- **Payload URL**: `https://your-server.com/webhook` (must be publicly reachable for GitHub)
- **Content type**: application/json
- **Events**: Push, Pull requests
- Save

## MongoDB schema

Each stored event has:

- `action`: `"push"` | `"pull_request"` | `"merge"`
- `author`: string
- `to_branch`: string
- `from_branch`: string (null for push)
- `timestamp`: datetime
- `repo`: repository full_name
- `created_at`: datetime

## API

- `GET /` — UI (polls `/api/events` every 15 seconds)
- `GET /api/events` — List latest events from MongoDB
- `POST /webhook` — GitHub webhook receiver (Push, Pull request)

## Local testing with ngrok

To receive GitHub webhooks on your machine:

```bash
ngrok http 5000
# Use the https URL as Payload URL in GitHub webhook
```
