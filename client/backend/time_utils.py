from datetime import datetime, timezone


def create_timestamp() -> str:
    """Create a consistent ISO format timestamp in UTC"""
    return datetime.now(timezone.utc).isoformat()


def format_db_timestamp(timestamp) -> str:
    """Format database timestamp consistently"""
    if hasattr(timestamp, 'astimezone'):
        # Convert to UTC and format as ISO string
        return timestamp.astimezone(timezone.utc).isoformat()
    elif isinstance(timestamp, str):
        # Already a string, but try to parse and normalize if needed
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            return timestamp  # Return as-is if can't parse
    else:
        return str(timestamp)  # Fallback
