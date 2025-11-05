# app/utils/progress.py
from typing import Dict
from threading import Lock

_progress: Dict[str, int] = {}
_lock = Lock()

def set_progress(task_id: str, percent: int):
    with _lock:
        _progress[task_id] = percent

def get_progress(task_id: str) -> int:
    with _lock:
        return _progress.get(task_id, 0)

def clear_progress(task_id: str):
    with _lock:
        if task_id in _progress:
            del _progress[task_id]
