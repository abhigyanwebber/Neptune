class IllegalRuntimeTransition(RuntimeError):
    """Raised when the runtime is asked to do something the current
    execution state does not allow (e.g. starting a turn on a session
    that has already completed)."""
