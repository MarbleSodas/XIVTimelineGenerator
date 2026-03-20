"""Timestamp normalization for FF Logs damage timeline events."""


def normalize_timestamps(events: list, fight_start_time: float) -> list:
    """Normalize all event timestamps to start at 0.

    Args:
        events: List of event dicts, each with a 'timestamp' key.
        fight_start_time: The fight start timestamp to subtract.

    Returns:
        A new list of events with normalized timestamps.
    """
    return [
        {**event, "timestamp": event["timestamp"] - fight_start_time}
        for event in events
    ]
