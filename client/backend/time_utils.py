"""Time utilities for making consistent timestamps in the database."""
from datetime import datetime, timezone


def create_timestamp() -> str:
    """Create a consistent ISO format timestamp in UTC"""
    return datetime.now(timezone.utc).isoformat()


def format_db_timestamp(timestamp) -> str:
    """Format database timestamp consistently"""
    if hasattr(timestamp, 'astimezone'):
        return timestamp.astimezone(timezone.utc).isoformat()
    if isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            return timestamp
    else:
        return str(timestamp)
