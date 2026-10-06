import pygame
import json
import threading
import time
from os.path import join
from collections import deque
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Generator, List, Optional
import numpy as np
from numpy.typing import NDArray

pygame.init()
font = pygame.font.Font(None, 50)

def debug(info, y = 10, x = 10):
	display_surface = pygame.display.get_surface()
	debug_surf = font.render(str(info),True,'White')
	debug_rect = debug_surf.get_rect(topleft = (x,y))
	display_surface.blit(debug_surf,debug_rect)

class ThreadSampleBuffer:
    """
    Isolated, memory-bounded buffer dedicated to a specific thread's metrics.

    Prevents data contention between threads by allocating isolated Deques
    for profiling categories. Ensures thread-safe metric aggregation.

    Args:
        max_samples (int): The maximum number of profiling samples to retain per category.
    """

    def __init__(self, max_samples: int) -> None:
        self.max_samples: int = max_samples
        self.categories: Dict[str, deque[float]] = {}
        self.lock: threading.Lock = threading.Lock()

    def record(self, category: str, elapsed_time: float) -> None:
        if category not in self.categories:
            with self.lock:
                if category not in self.categories:
                    self.categories[category] = deque(maxlen=self.max_samples)
        self.categories[category].append(elapsed_time)


class Profiler:
    """
    Production-grade game telemetry system.
    """

    def __init__(self, max_samples_per_category: int = 10000) -> None:
        self.max_samples: int = max_samples_per_category
        self.registry_lock: threading.Lock = threading.Lock()
        self.thread_buffers: Dict[int, ThreadSampleBuffer] = {}
        self.frame_start_time: float = 0.0
        # Change this to False to completely silence/stop the profiler project-wide
        self.enabled: bool = False

    def _get_buffer(self) -> ThreadSampleBuffer:
        thread_id: int = threading.get_ident()
        if thread_id in self.thread_buffers:
            return self.thread_buffers[thread_id]

        with self.registry_lock:
            if thread_id not in self.thread_buffers:
                self.thread_buffers[thread_id] = ThreadSampleBuffer(self.max_samples)
            return self.thread_buffers[thread_id]

    def start_frame(self) -> None:
        if not self.enabled: return  # Short-circuit
        self.frame_start_time = time.perf_counter()

    def end_frame(self) -> None:
        if not self.enabled: return  # Short-circuit
        if self.frame_start_time > 0:
            self.record('Frame_Total', time.perf_counter() - self.frame_start_time)

    def record(self, category: str, elapsed_time: float) -> None:
        if not self.enabled: return  # Short-circuit
        buf: ThreadSampleBuffer = self._get_buffer()
        buf.record(category, elapsed_time)

    @contextmanager
    def measure(self, category: str) -> Generator[None, None, None]:
        if not self.enabled:
            yield
            return  # Run the code inside the 'with' block block normally, but don't track time
            
        start_time: float = time.perf_counter()
        try:
            yield
        finally:
            self.record(category, time.perf_counter() - start_time)

    def profile_func(self, category: Optional[str] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            cat: str = category or f"{func.__module__}.{func.__qualname__}"

            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Dynamic check: executes without tracking overhead if self.enabled is False
                if not self.enabled:
                    return func(*args, **kwargs)
                with self.measure(cat):
                    return func(*args, **kwargs)

            return wrapper

        return decorator

    def save_report(self, directory: Optional[str] = None, filename: str = 'profiling_results.json') -> None:
        if not self.enabled:
            print('[TELEMETRY] Profiler is disabled. No report generated.')
            return

        print('\n[TELEMETRY] Compiling engine metrics from all threads...')
        master_records: Dict[str, List[float]] = {}

        with self.registry_lock:
            for thread_id, buf in self.thread_buffers.items():
                with buf.lock:
                    for category, samples in buf.categories.items():
                        if category not in master_records:
                            master_records[category] = []
                        master_records[category].extend(list(samples))

        report: Dict[str, Dict[str, Any]] = {}
        for category, times in master_records.items():
            if not times:
                continue

            arr: NDArray[np.float64] = np.array(times, dtype=np.float64) * 1000.0
            report[category] = {
                'Calls': len(arr),
                'Avg_ms': round(float(np.mean(arr)), 3),
                'Min_ms': round(float(np.min(arr)), 3),
                'Max_ms': round(float(np.max(arr)), 3),
                'P99_ms': round(float(np.percentile(arr, 99)), 3),
                'Total_Time_ms': round(float(np.sum(arr)), 3),
            }

        filepath = join(directory, filename) if directory else filename
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=4)
            print(f'[TELEMETRY] Report successfully saved to {filepath}')
        except Exception as e:
            print(f'[TELEMETRY] ERROR: Failed to write report file: {e}')


global_profiler: Profiler = Profiler()