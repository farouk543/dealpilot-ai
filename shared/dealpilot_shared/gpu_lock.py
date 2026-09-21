import contextlib
import fcntl
import os

_DEFAULT_LOCK_PATH = "/data/gpu_lock/gpu.lock"


@contextlib.contextmanager
def gpu_lock():
    """Cross-process, cross-container mutex around the host's single GPU.

    interior-render (SDXL) and exterior-render (Cycles) run in separate
    containers, so a plain threading.Lock inside either process cannot stop
    them from touching the GPU at the same time. Confirmed in practice: both
    running concurrently pushed VRAM to within ~250MB of this card's 8GB
    limit and roughly doubled each other's generation time (45s->80s,
    15-25s->81s) — not a crash yet, but no safety margin left either.

    Backed by flock() on a file in a Docker volume mounted into both
    services (GPU_LOCK_PATH, default /data/gpu_lock/gpu.lock) — no new
    dependency, works across containers the same way it would across
    unrelated processes on one host.
    """
    lock_path = os.environ.get("GPU_LOCK_PATH", _DEFAULT_LOCK_PATH)
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
