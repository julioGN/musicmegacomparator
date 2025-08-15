"""
Metrics and monitoring utilities for MusicWeb.

Provides application metrics, performance monitoring, and analytics.
"""

import time
import functools
from typing import Dict, Any, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading
import json
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Collects and aggregates application metrics."""
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._metrics = defaultdict(list)
        self._counters = defaultdict(int)
        self._timers = defaultdict(deque)
        self._gauges = defaultdict(float)
        self._lock = threading.Lock()
        
    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a counter metric."""
        with self._lock:
            key = self._make_key(name, tags)
            self._counters[key] += value
            logger.debug(f"Counter {key} incremented by {value}")
    
    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Record a timing metric."""
        with self._lock:
            key = self._make_key(name, tags)
            self._timers[key].append({
                'timestamp': datetime.now(),
                'duration': duration
            })
            
            # Keep only recent samples
            while len(self._timers[key]) > self.max_samples:
                self._timers[key].popleft()
                
            logger.debug(f"Timer {key} recorded: {duration:.3f}s")
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric."""
        with self._lock:
            key = self._make_key(name, tags)
            self._gauges[key] = value
            logger.debug(f"Gauge {key} set to {value}")
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a histogram metric."""
        with self._lock:
            key = self._make_key(name, tags)
            self._metrics[key].append({
                'timestamp': datetime.now(),
                'value': value
            })
            
            # Keep only recent samples
            while len(self._metrics[key]) > self.max_samples:
                self._metrics[key].pop(0)
                
            logger.debug(f"Histogram {key} recorded: {value}")
    
    def get_counter(self, name: str, tags: Dict[str, str] = None) -> int:
        """Get counter value."""
        key = self._make_key(name, tags)
        return self._counters.get(key, 0)
    
    def get_gauge(self, name: str, tags: Dict[str, str] = None) -> float:
        """Get gauge value."""
        key = self._make_key(name, tags)
        return self._gauges.get(key, 0.0)
    
    def get_timer_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        """Get timer statistics."""
        key = self._make_key(name, tags)
        timers = self._timers.get(key, deque())
        
        if not timers:
            return {'count': 0, 'avg': 0, 'min': 0, 'max': 0}
        
        durations = [t['duration'] for t in timers]
        return {
            'count': len(durations),
            'avg': sum(durations) / len(durations),
            'min': min(durations),
            'max': max(durations),
            'sum': sum(durations)
        }
    
    def get_histogram_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        """Get histogram statistics."""
        key = self._make_key(name, tags)
        values = [m['value'] for m in self._metrics.get(key, [])]
        
        if not values:
            return {'count': 0, 'avg': 0, 'min': 0, 'max': 0}
        
        return {
            'count': len(values),
            'avg': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'sum': sum(values)
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            return {
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'timers': {k: self.get_timer_stats(k.split('|')[0], 
                                                 self._parse_tags(k.split('|')[1:]))
                          for k in self._timers.keys()},
                'histograms': {k: self.get_histogram_stats(k.split('|')[0],
                                                         self._parse_tags(k.split('|')[1:]))
                             for k in self._metrics.keys()},
                'timestamp': datetime.now().isoformat()
            }
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._timers.clear()
            self._gauges.clear()
            logger.info("All metrics reset")
    
    def export_to_file(self, file_path: str):
        """Export metrics to JSON file."""
        metrics = self.get_all_metrics()
        with open(file_path, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        logger.info(f"Metrics exported to {file_path}")
    
    def _make_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """Create a unique key for the metric."""
        if not tags:
            return name
        
        tag_str = '|'.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}|{tag_str}"
    
    def _parse_tags(self, tag_parts: list) -> Dict[str, str]:
        """Parse tags from key parts."""
        tags = {}
        for part in tag_parts:
            if '=' in part:
                k, v = part.split('=', 1)
                tags[k] = v
        return tags


# Global metrics collector instance
metrics = MetricsCollector()


def timer(name: str, tags: Dict[str, str] = None):
    """Decorator to time function execution."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                success_tags = dict(tags) if tags else {}
                success_tags['status'] = 'success'
                metrics.record_timer(name, time.time() - start_time, success_tags)
                return result
            except Exception as e:
                error_tags = dict(tags) if tags else {}
                error_tags['status'] = 'error'
                error_tags['error_type'] = type(e).__name__
                metrics.record_timer(name, time.time() - start_time, error_tags)
                raise
        return wrapper
    return decorator


def counter(name: str, tags: Dict[str, str] = None):
    """Decorator to count function calls."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                success_tags = dict(tags) if tags else {}
                success_tags['status'] = 'success'
                metrics.increment_counter(name, 1, success_tags)
                return result
            except Exception as e:
                error_tags = dict(tags) if tags else {}
                error_tags['status'] = 'error'
                error_tags['error_type'] = type(e).__name__
                metrics.increment_counter(name, 1, error_tags)
                raise
        return wrapper
    return decorator


class PerformanceMonitor:
    """Monitor application performance."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.response_times = deque(maxlen=window_size)
        self.error_count = 0
        self.total_requests = 0
        self._lock = threading.Lock()
    
    def record_request(self, duration: float, success: bool = True):
        """Record a request."""
        with self._lock:
            self.response_times.append(duration)
            self.total_requests += 1
            if not success:
                self.error_count += 1
    
    def get_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        with self._lock:
            if not self.response_times:
                return {
                    'avg_response_time': 0,
                    'min_response_time': 0,
                    'max_response_time': 0,
                    'error_rate': 0,
                    'requests_per_second': 0
                }
            
            response_times = list(self.response_times)
            return {
                'avg_response_time': sum(response_times) / len(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'error_rate': self.error_count / self.total_requests if self.total_requests > 0 else 0,
                'total_requests': self.total_requests,
                'error_count': self.error_count
            }


class ApplicationMetrics:
    """High-level application metrics."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.feature_usage = defaultdict(int)
        self.user_sessions = set()
        self.platform_usage = defaultdict(int)
        self.file_formats = defaultdict(int)
        self._lock = threading.Lock()
    
    def track_feature_usage(self, feature: str, user_id: str = None):
        """Track feature usage."""
        with self._lock:
            self.feature_usage[feature] += 1
            if user_id:
                self.user_sessions.add(user_id)
            metrics.increment_counter('feature.usage', tags={'feature': feature})
    
    def track_platform_usage(self, platform: str):
        """Track platform usage."""
        with self._lock:
            self.platform_usage[platform] += 1
            metrics.increment_counter('platform.usage', tags={'platform': platform})
    
    def track_file_format(self, format_type: str):
        """Track file format usage."""
        with self._lock:
            self.file_formats[format_type] += 1
            metrics.increment_counter('file.format', tags={'format': format_type})
    
    def get_application_stats(self) -> Dict[str, Any]:
        """Get application statistics."""
        with self._lock:
            uptime = datetime.now() - self.start_time
            return {
                'uptime_seconds': uptime.total_seconds(),
                'uptime_hours': uptime.total_seconds() / 3600,
                'unique_sessions': len(self.user_sessions),
                'feature_usage': dict(self.feature_usage),
                'platform_usage': dict(self.platform_usage),
                'file_formats': dict(self.file_formats),
                'total_feature_uses': sum(self.feature_usage.values())
            }


# Global application metrics
app_metrics = ApplicationMetrics()


class HealthChecker:
    """Application health checker."""
    
    def __init__(self):
        self.checks = {}
        self.last_check = None
    
    def register_check(self, name: str, check_func: Callable[[], bool]):
        """Register a health check."""
        self.checks[name] = check_func
    
    def run_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        overall_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = check_func()
                duration = time.time() - start_time
                
                results[name] = {
                    'healthy': result,
                    'duration': duration,
                    'timestamp': datetime.now().isoformat()
                }
                
                if not result:
                    overall_healthy = False
                    
            except Exception as e:
                results[name] = {
                    'healthy': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                overall_healthy = False
        
        self.last_check = datetime.now()
        
        return {
            'overall_healthy': overall_healthy,
            'checks': results,
            'timestamp': datetime.now().isoformat()
        }


# Global health checker
health_checker = HealthChecker()


# Default health checks
def basic_health_check() -> bool:
    """Basic health check."""
    return True


def memory_health_check() -> bool:
    """Memory usage health check."""
    try:
        import psutil
        memory_percent = psutil.virtual_memory().percent
        return memory_percent < 90  # Alert if memory usage > 90%
    except ImportError:
        return True  # Skip if psutil not available


def disk_health_check() -> bool:
    """Disk usage health check."""
    try:
        import psutil
        disk_percent = psutil.disk_usage('/').percent
        return disk_percent < 90  # Alert if disk usage > 90%
    except ImportError:
        return True  # Skip if psutil not available


# Register default health checks
health_checker.register_check('basic', basic_health_check)
health_checker.register_check('memory', memory_health_check)
health_checker.register_check('disk', disk_health_check)


def export_metrics_to_prometheus(file_path: str = None):
    """Export metrics in Prometheus format."""
    if file_path is None:
        file_path = "metrics.prom"
    
    prometheus_metrics = []
    all_metrics = metrics.get_all_metrics()
    
    # Export counters
    for name, value in all_metrics['counters'].items():
        clean_name = name.replace('|', '_').replace('=', '_').replace('-', '_')
        prometheus_metrics.append(f"musicweb_{clean_name}_total {value}")
    
    # Export gauges
    for name, value in all_metrics['gauges'].items():
        clean_name = name.replace('|', '_').replace('=', '_').replace('-', '_')
        prometheus_metrics.append(f"musicweb_{clean_name} {value}")
    
    # Export timer averages
    for name, stats in all_metrics['timers'].items():
        clean_name = name.replace('|', '_').replace('=', '_').replace('-', '_')
        prometheus_metrics.append(f"musicweb_{clean_name}_duration_seconds {stats['avg']}")
        prometheus_metrics.append(f"musicweb_{clean_name}_count {stats['count']}")
    
    with open(file_path, 'w') as f:
        f.write('\n'.join(prometheus_metrics))
    
    logger.info(f"Prometheus metrics exported to {file_path}")


# Streamlit metrics for web interface
def get_streamlit_metrics() -> Dict[str, Any]:
    """Get metrics formatted for Streamlit display."""
    all_metrics = metrics.get_all_metrics()
    app_stats = app_metrics.get_application_stats()
    health_status = health_checker.run_checks()
    
    return {
        'system_metrics': all_metrics,
        'application_stats': app_stats,
        'health_status': health_status,
        'performance': {
            'uptime_hours': app_stats['uptime_hours'],
            'total_requests': all_metrics['counters'].get('requests_total', 0),
            'error_rate': health_status.get('error_rate', 0)
        }
    }