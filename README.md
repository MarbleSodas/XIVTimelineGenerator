# XIVTimelineGenerator

FFLogs report fetcher with a Textual TUI.

## Setup

```bash
# Create virtual environment
python3 -m venv .venv

# Install dependencies
.venv/bin/pip install -e .
```

## Running

```bash
# Set FFLogs credentials
export FFLOGS_CLIENT_ID=your_client_id
export FFLOGS_CLIENT_SECRET=your_client_secret

# Activate venv and run
source .venv/bin/activate
python -m tui.app
```