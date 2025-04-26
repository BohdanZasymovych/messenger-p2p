#!/bin/bash

# Start the FastAPI application in the background
python messenger.py &

# Wait for server to start
echo "Waiting for server to start..."
sleep 5

# Print instructions for accessing the web interface
echo ""
echo "====================================================="
echo "  Chat application is running!"
echo ""
echo "  Access the web interface at: http://localhost:8000"
echo ""
echo "  If you're running this locally, the browser should"
echo "  open automatically. If not, please open the URL"
echo "  manually in your browser."
echo "====================================================="
echo ""

# Try to open browser if we're in an environment that supports it
if [ -n "$DISPLAY" ]; then
    # Try different commands to open browser
    xdg-open http://localhost:8000 2>/dev/null || \
    open http://localhost:8000 2>/dev/null || \
    python -m webbrowser http://localhost:8000 2>/dev/null &
fi

# Keep the container running
wait