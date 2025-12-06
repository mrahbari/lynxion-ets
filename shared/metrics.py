"""
Metrics collection service for the enterprise hedge fund trading system.
This service collects and aggregates performance metrics across all components.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import time
import threading
from enum import Enum


class MetricType(Enum):
    """Types of metrics that can be collected"""
    PERFORMANCE = "performance"
    ERROR = "error"
    BUSINESS = "business"
    SYSTEM = "system"


class MetricsCollector:
    """Service to collect and aggregate metrics across the trading system"""
    
    def __init__(self):
        self.metrics_store: Dict[str, List[Dict[str, Any]]] = {}
        self.aggregated_metrics: Dict[str, Any] = {}
        self.lock = threading.Lock()
        
    def record_metric(self, 
                     metric_name: str, 
                     metric_type: MetricType, 
                     value: float, 
                     tags: Optional[Dict[str, str]] = None,
                     timestamp: Optional[datetime] = None):
        """Record a metric with optional tags and timestamp"""
        with self.lock:
            if metric_name not in self.metrics_store:
                self.metrics_store[metric_name] = []
            
            metric_record = {
                'timestamp': timestamp or datetime.now(),
                'value': value,
                'type': metric_type.value,
                'tags': tags or {},
                'metric_name': metric_name
            }
            
            self.metrics_store[metric_name].append(metric_record)
    
    def record_performance_metric(self, operation: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record a performance metric"""
        self.record_metric(
            metric_name=f"performance.{operation}",
            metric_type=MetricType.PERFORMANCE,
            value=duration,
            tags=tags
        )
    
    def record_error_metric(self, error_type: str, count: int = 1, tags: Optional[Dict[str, str]] = None):
        """Record an error metric"""
        self.record_metric(
            metric_name=f"errors.{error_type}",
            metric_type=MetricType.ERROR,
            value=count,
            tags=tags
        )
    
    def get_metric_history(self, metric_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history for a specific metric"""
        with self.lock:
            if metric_name in self.metrics_store:
                return self.metrics_store[metric_name][-limit:]
            return []
    
    def get_aggregated_metric(self, metric_name: str) -> Dict[str, float]:
        """Get aggregated statistics for a specific metric"""
        with self.lock:
            if metric_name in self.metrics_store:
                values = [record['value'] for record in self.metrics_store[metric_name]]
                if not values:
                    return {}
                
                return {
                    'count': len(values),
                    'sum': sum(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values)
                }
            return {}
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        with self.lock:
            return {name: self.get_aggregated_metric(name) for name in self.metrics_store.keys()}
    
    def reset_metrics(self):
        """Reset all collected metrics"""
        with self.lock:
            self.metrics_store.clear()


# Global metrics collector instance
metrics_collector = MetricsCollector()


class PerformanceTimer:
    """Context manager and decorator for timing operations"""
    
    def __init__(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        self.operation_name = operation_name
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        metrics_collector.record_performance_metric(self.operation_name, duration, self.tags)
        
        # Log if the operation took longer than expected
        if duration > 0.1:  # 100ms threshold
            from shared.logger import logger
            logger.warning(f"Slow operation detected: {self.operation_name} took {duration:.4f}s", **self.tags)


def time_operation(operation_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for timing function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with PerformanceTimer(operation_name, tags):
                return func(*args, **kwargs)
        return wrapper
    return decorator