"""
Automation Analytics System

This module provides comprehensive analytics, performance tracking, metrics collection,
optimization suggestions, and reporting capabilities for the automation system.

Features:
- Real-time performance monitoring
- Detailed execution analytics  
- Resource utilization tracking
- Optimization recommendations
- Comprehensive reporting system
- Predictive analytics and forecasting
- Anomaly detection
- Performance benchmarking
"""

import time
import threading
import logging
import sqlite3
import json
import statistics
import math
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import uuid
from collections import defaultdict, deque
import weakref

# Statistical analysis
try:
    import numpy as np
    import scipy.stats as stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Data visualization
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"         # Cumulative count
    GAUGE = "gauge"            # Point-in-time value
    HISTOGRAM = "histogram"    # Distribution of values
    TIMER = "timer"            # Execution time
    RATE = "rate"              # Rate per unit time

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AnalyticsInterval(Enum):
    """Analytics collection intervals"""
    REAL_TIME = "real_time"    # Immediate
    MINUTE = "minute"          # Every minute
    HOUR = "hour"             # Every hour
    DAY = "day"               # Daily
    WEEK = "week"             # Weekly
    MONTH = "month"           # Monthly

@dataclass
class MetricPoint:
    """Individual metric data point"""
    metric_name: str
    value: Union[int, float]
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Execution metrics
    total_tasks_executed: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_execution_time: float = 0.0
    max_execution_time: float = 0.0
    min_execution_time: float = 0.0
    
    # Resource metrics
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    disk_usage_percent: float = 0.0
    network_io_mbps: float = 0.0
    
    # Throughput metrics
    tasks_per_minute: float = 0.0
    tasks_per_hour: float = 0.0
    success_rate_percent: float = 0.0
    
    # Queue metrics
    pending_tasks: int = 0
    active_tasks: int = 0
    queue_wait_time: float = 0.0
    
    # Error metrics
    error_rate_percent: float = 0.0
    timeout_count: int = 0
    retry_count: int = 0

@dataclass
class OptimizationSuggestion:
    """Performance optimization suggestion"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    category: str = ""
    impact_level: str = "medium"  # low, medium, high, critical
    confidence_score: float = 0.0
    estimated_improvement: str = ""
    implementation_effort: str = "medium"  # low, medium, high
    suggested_actions: List[str] = field(default_factory=list)
    related_metrics: List[str] = field(default_factory=list)
    created_time: datetime = field(default_factory=datetime.now)

@dataclass
class AnalyticsAlert:
    """Analytics alert"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    message: str = ""
    level: AlertLevel = AlertLevel.INFO
    metric_name: str = ""
    threshold_value: float = 0.0
    actual_value: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False

@dataclass
class PerformanceReport:
    """Comprehensive performance report"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    report_type: str = ""
    period_start: datetime = field(default_factory=datetime.now)
    period_end: datetime = field(default_factory=datetime.now)
    
    # Summary metrics
    summary_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    
    # Detailed data
    execution_trends: List[Dict[str, Any]] = field(default_factory=list)
    resource_trends: List[Dict[str, Any]] = field(default_factory=list)
    error_analysis: List[Dict[str, Any]] = field(default_factory=list)
    
    # Insights
    key_insights: List[str] = field(default_factory=list)
    optimization_suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    performance_score: float = 0.0
    
    # Generated content
    charts_generated: List[str] = field(default_factory=list)
    generated_time: datetime = field(default_factory=datetime.now)

class MetricStore:
    """
    Thread-safe storage for metrics data
    """
    
    def __init__(self, max_points_per_metric: int = 10000):
        self.max_points_per_metric = max_points_per_metric
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points_per_metric))
        self.aggregated_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
    
    def add_metric(self, metric: MetricPoint):
        """Add metric point"""
        with self._lock:
            self.metrics[metric.metric_name].append(metric)
            self._update_aggregated_metrics(metric)
    
    def get_metrics(self, metric_name: str, start_time: datetime = None, 
                   end_time: datetime = None) -> List[MetricPoint]:
        """Get metric points for a specific metric"""
        with self._lock:
            points = list(self.metrics[metric_name])
        
        if start_time or end_time:
            filtered_points = []
            for point in points:
                if start_time and point.timestamp < start_time:
                    continue
                if end_time and point.timestamp > end_time:
                    continue
                filtered_points.append(point)
            return filtered_points
        
        return points
    
    def get_latest_value(self, metric_name: str) -> Optional[Union[int, float]]:
        """Get latest value for metric"""
        with self._lock:
            if metric_name in self.metrics and self.metrics[metric_name]:
                return self.metrics[metric_name][-1].value
        return None
    
    def get_aggregated_stats(self, metric_name: str) -> Dict[str, float]:
        """Get aggregated statistics for metric"""
        with self._lock:
            return self.aggregated_metrics.get(metric_name, {})
    
    def get_all_metric_names(self) -> List[str]:
        """Get all metric names"""
        with self._lock:
            return list(self.metrics.keys())
    
    def clear_old_data(self, before_time: datetime):
        """Clear old metric data"""
        with self._lock:
            for metric_name in list(self.metrics.keys()):
                points = self.metrics[metric_name]
                # Remove old points
                while points and points[0].timestamp < before_time:
                    points.popleft()
                
                # Recalculate aggregated metrics
                if points:
                    self._recalculate_aggregated_metrics(metric_name)
    
    def _update_aggregated_metrics(self, metric: MetricPoint):
        """Update aggregated metrics for a metric"""
        metric_name = metric.metric_name
        points = list(self.metrics[metric_name])
        
        if not points:
            return
        
        values = [p.value for p in points]
        
        # Calculate basic statistics
        self.aggregated_metrics[metric_name] = {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
            'latest': values[-1],
            'first': values[0]
        }
        
        # Additional percentiles if scipy available
        if SCIPY_AVAILABLE and len(values) > 10:
            percentiles = np.percentile(values, [25, 75, 90, 95, 99])
            self.aggregated_metrics[metric_name].update({
                'p25': percentiles[0],
                'p75': percentiles[1],
                'p90': percentiles[2],
                'p95': percentiles[3],
                'p99': percentiles[4]
            })
    
    def _recalculate_aggregated_metrics(self, metric_name: str):
        """Recalculate aggregated metrics after data cleanup"""
        if metric_name in self.metrics and self.metrics[metric_name]:
            # Create a dummy point to trigger recalculation
            latest_point = self.metrics[metric_name][-1]
            self._update_aggregated_metrics(latest_point)

class PerformanceMonitor:
    """
    Real-time performance monitoring system
    """
    
    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.metric_store = MetricStore()
        self.logger = logging.getLogger(__name__)
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Custom metric collectors
        self.custom_collectors: List[Callable[[], List[MetricPoint]]] = []
        
        # Alert thresholds
        self.alert_thresholds: Dict[str, Dict[str, float]] = {}
        self.alert_callbacks: List[Callable[[AnalyticsAlert], None]] = []
        
        # Resource monitoring
        try:
            import psutil
            self.psutil = psutil
            self.psutil_available = True
        except ImportError:
            self.psutil_available = False
    
    def start_monitoring(self):
        """Start performance monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("Performance monitoring stopped")
    
    def add_custom_collector(self, collector: Callable[[], List[MetricPoint]]):
        """Add custom metric collector"""
        self.custom_collectors.append(collector)
    
    def set_alert_threshold(self, metric_name: str, threshold_type: str, 
                          threshold_value: float):
        """Set alert threshold for metric"""
        if metric_name not in self.alert_thresholds:
            self.alert_thresholds[metric_name] = {}
        self.alert_thresholds[metric_name][threshold_type] = threshold_value
    
    def add_alert_callback(self, callback: Callable[[AnalyticsAlert], None]):
        """Add alert callback function"""
        self.alert_callbacks.append(callback)
    
    def record_metric(self, name: str, value: Union[int, float], 
                     tags: Dict[str, str] = None, metadata: Dict[str, Any] = None):
        """Record custom metric"""
        metric = MetricPoint(
            metric_name=name,
            value=value,
            tags=tags or {},
            metadata=metadata or {}
        )
        self.metric_store.add_metric(metric)
        
        # Check for alerts
        self._check_metric_alerts(metric)
    
    def record_execution_time(self, operation_name: str, execution_time: float,
                            success: bool = True, tags: Dict[str, str] = None):
        """Record operation execution time"""
        base_tags = tags or {}
        base_tags['success'] = str(success)
        
        # Record execution time
        self.record_metric(f"{operation_name}.execution_time", execution_time, base_tags)
        
        # Record execution count
        self.record_metric(f"{operation_name}.executions", 1, base_tags)
        
        # Record success/failure
        if success:
            self.record_metric(f"{operation_name}.success", 1, base_tags)
        else:
            self.record_metric(f"{operation_name}.failure", 1, base_tags)
    
    def get_performance_snapshot(self) -> PerformanceMetrics:
        """Get current performance snapshot"""
        metrics = PerformanceMetrics()
        current_time = datetime.now()
        
        # Get execution metrics
        execution_times = self.metric_store.get_metrics("automation.execution_time", 
                                                       current_time - timedelta(minutes=5))
        if execution_times:
            times = [m.value for m in execution_times]
            metrics.average_execution_time = statistics.mean(times)
            metrics.max_execution_time = max(times)
            metrics.min_execution_time = min(times)
        
        # Get success/failure counts
        successes = self.metric_store.get_metrics("automation.success",
                                                current_time - timedelta(minutes=5))
        failures = self.metric_store.get_metrics("automation.failure",
                                               current_time - timedelta(minutes=5))
        
        metrics.successful_executions = len(successes)
        metrics.failed_executions = len(failures)
        metrics.total_tasks_executed = metrics.successful_executions + metrics.failed_executions
        
        if metrics.total_tasks_executed > 0:
            metrics.success_rate_percent = (metrics.successful_executions / 
                                          metrics.total_tasks_executed) * 100
            metrics.error_rate_percent = (metrics.failed_executions / 
                                        metrics.total_tasks_executed) * 100
        
        # Get throughput
        if metrics.total_tasks_executed > 0:
            metrics.tasks_per_minute = metrics.total_tasks_executed
            metrics.tasks_per_hour = metrics.total_tasks_executed * 12  # Extrapolate from 5-min window
        
        # Get resource usage
        if self.psutil_available:
            try:
                metrics.cpu_usage_percent = self.psutil.cpu_percent()
                memory = self.psutil.virtual_memory()
                metrics.memory_usage_mb = memory.used / (1024 * 1024)
                disk = self.psutil.disk_usage('/')
                metrics.disk_usage_percent = disk.percent
            except Exception as e:
                self.logger.debug(f"Failed to get system metrics: {e}")
        
        # Get queue metrics
        pending_tasks = self.metric_store.get_latest_value("automation.pending_tasks") or 0
        active_tasks = self.metric_store.get_latest_value("automation.active_tasks") or 0
        
        metrics.pending_tasks = int(pending_tasks)
        metrics.active_tasks = int(active_tasks)
        
        return metrics
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                current_time = datetime.now()
                
                # Collect system metrics
                self._collect_system_metrics()
                
                # Run custom collectors
                for collector in self.custom_collectors:
                    try:
                        collected_metrics = collector()
                        for metric in collected_metrics:
                            self.metric_store.add_metric(metric)
                    except Exception as e:
                        self.logger.error(f"Custom collector error: {e}")
                
                # Clean old data (keep 24 hours)
                cutoff_time = current_time - timedelta(hours=24)
                self.metric_store.clear_old_data(cutoff_time)
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                self.logger.error(f"Monitor loop error: {e}")
                time.sleep(5.0)
    
    def _collect_system_metrics(self):
        """Collect system resource metrics"""
        if not self.psutil_available:
            return
        
        try:
            current_time = datetime.now()
            
            # CPU metrics
            cpu_percent = self.psutil.cpu_percent()
            self.record_metric("system.cpu_percent", cpu_percent)
            
            # Memory metrics
            memory = self.psutil.virtual_memory()
            self.record_metric("system.memory_percent", memory.percent)
            self.record_metric("system.memory_used_mb", memory.used / (1024 * 1024))
            
            # Disk metrics
            disk = self.psutil.disk_usage('/')
            self.record_metric("system.disk_percent", disk.percent)
            
            # Process count
            process_count = len(self.psutil.pids())
            self.record_metric("system.process_count", process_count)
            
        except Exception as e:
            self.logger.debug(f"System metrics collection failed: {e}")
    
    def _check_metric_alerts(self, metric: MetricPoint):
        """Check if metric triggers any alerts"""
        metric_name = metric.metric_name
        
        if metric_name not in self.alert_thresholds:
            return
        
        thresholds = self.alert_thresholds[metric_name]
        
        for threshold_type, threshold_value in thresholds.items():
            alert_triggered = False
            alert_level = AlertLevel.WARNING
            
            if threshold_type == "max" and metric.value > threshold_value:
                alert_triggered = True
                alert_level = AlertLevel.ERROR if metric.value > threshold_value * 1.5 else AlertLevel.WARNING
                
            elif threshold_type == "min" and metric.value < threshold_value:
                alert_triggered = True
                alert_level = AlertLevel.WARNING
            
            if alert_triggered:
                alert = AnalyticsAlert(
                    title=f"{metric_name} threshold exceeded",
                    message=f"{metric_name} value {metric.value} {threshold_type} threshold {threshold_value}",
                    level=alert_level,
                    metric_name=metric_name,
                    threshold_value=threshold_value,
                    actual_value=metric.value
                )
                
                # Call alert callbacks
                for callback in self.alert_callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        self.logger.error(f"Alert callback error: {e}")

class OptimizationAnalyzer:
    """
    Analyzes performance data and suggests optimizations
    """
    
    def __init__(self, metric_store: MetricStore):
        self.metric_store = metric_store
        self.logger = logging.getLogger(__name__)
        
        # Analysis rules
        self.optimization_rules = []
        self._setup_default_rules()
    
    def analyze_performance(self, time_window: timedelta = None) -> List[OptimizationSuggestion]:
        """Analyze performance and generate optimization suggestions"""
        time_window = time_window or timedelta(hours=1)
        end_time = datetime.now()
        start_time = end_time - time_window
        
        suggestions = []
        
        # Run all optimization rules
        for rule in self.optimization_rules:
            try:
                rule_suggestions = rule(self.metric_store, start_time, end_time)
                suggestions.extend(rule_suggestions)
            except Exception as e:
                self.logger.error(f"Optimization rule error: {e}")
        
        # Sort by impact level and confidence
        impact_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        
        suggestions.sort(
            key=lambda s: (impact_weights.get(s.impact_level, 0), s.confidence_score),
            reverse=True
        )
        
        return suggestions[:10]  # Return top 10 suggestions
    
    def add_optimization_rule(self, rule: Callable):
        """Add custom optimization rule"""
        self.optimization_rules.append(rule)
    
    def _setup_default_rules(self):
        """Set up default optimization rules"""
        
        def high_cpu_usage_rule(metric_store, start_time, end_time):
            """Check for high CPU usage"""
            suggestions = []
            cpu_metrics = metric_store.get_metrics("system.cpu_percent", start_time, end_time)
            
            if cpu_metrics:
                avg_cpu = statistics.mean([m.value for m in cpu_metrics])
                if avg_cpu > 80:
                    suggestions.append(OptimizationSuggestion(
                        title="High CPU Usage Detected",
                        description=f"Average CPU usage is {avg_cpu:.1f}% over the analysis period",
                        category="performance",
                        impact_level="high",
                        confidence_score=0.9,
                        estimated_improvement="10-30% performance increase",
                        implementation_effort="medium",
                        suggested_actions=[
                            "Optimize CPU-intensive operations",
                            "Consider task parallelization",
                            "Review algorithm efficiency",
                            "Scale horizontally if needed"
                        ],
                        related_metrics=["system.cpu_percent", "automation.execution_time"]
                    ))
            
            return suggestions
        
        def high_memory_usage_rule(metric_store, start_time, end_time):
            """Check for high memory usage"""
            suggestions = []
            memory_metrics = metric_store.get_metrics("system.memory_percent", start_time, end_time)
            
            if memory_metrics:
                avg_memory = statistics.mean([m.value for m in memory_metrics])
                if avg_memory > 85:
                    suggestions.append(OptimizationSuggestion(
                        title="High Memory Usage Detected",
                        description=f"Average memory usage is {avg_memory:.1f}% over the analysis period",
                        category="performance",
                        impact_level="high",
                        confidence_score=0.8,
                        estimated_improvement="15-25% memory reduction",
                        implementation_effort="medium",
                        suggested_actions=[
                            "Implement memory pooling",
                            "Optimize data structures",
                            "Add garbage collection tuning",
                            "Consider caching strategies"
                        ],
                        related_metrics=["system.memory_percent", "system.memory_used_mb"]
                    ))
            
            return suggestions
        
        def high_error_rate_rule(metric_store, start_time, end_time):
            """Check for high error rates"""
            suggestions = []
            
            # Get execution metrics
            successes = metric_store.get_metrics("automation.success", start_time, end_time)
            failures = metric_store.get_metrics("automation.failure", start_time, end_time)
            
            if successes or failures:
                success_count = len(successes)
                failure_count = len(failures)
                total_count = success_count + failure_count
                
                if total_count > 0:
                    error_rate = (failure_count / total_count) * 100
                    
                    if error_rate > 10:  # > 10% error rate
                        suggestions.append(OptimizationSuggestion(
                            title="High Error Rate Detected",
                            description=f"Error rate is {error_rate:.1f}% over the analysis period",
                            category="reliability",
                            impact_level="critical" if error_rate > 25 else "high",
                            confidence_score=0.95,
                            estimated_improvement="50-80% error reduction",
                            implementation_effort="high",
                            suggested_actions=[
                                "Improve error handling and retry logic",
                                "Add input validation",
                                "Review failure patterns",
                                "Implement circuit breaker patterns"
                            ],
                            related_metrics=["automation.success", "automation.failure"]
                        ))
            
            return suggestions
        
        def slow_execution_rule(metric_store, start_time, end_time):
            """Check for slow execution times"""
            suggestions = []
            execution_metrics = metric_store.get_metrics("automation.execution_time", start_time, end_time)
            
            if execution_metrics and len(execution_metrics) > 10:
                times = [m.value for m in execution_metrics]
                avg_time = statistics.mean(times)
                p95_time = np.percentile(times, 95) if SCIPY_AVAILABLE else max(times)
                
                if avg_time > 30 or p95_time > 60:  # 30s average or 60s p95
                    suggestions.append(OptimizationSuggestion(
                        title="Slow Execution Times Detected",
                        description=f"Average execution time: {avg_time:.1f}s, P95: {p95_time:.1f}s",
                        category="performance",
                        impact_level="medium",
                        confidence_score=0.8,
                        estimated_improvement="20-40% speed improvement",
                        implementation_effort="medium",
                        suggested_actions=[
                            "Profile slow operations",
                            "Optimize database queries",
                            "Add caching layers",
                            "Consider async processing"
                        ],
                        related_metrics=["automation.execution_time"]
                    ))
            
            return suggestions
        
        def queue_buildup_rule(metric_store, start_time, end_time):
            """Check for task queue buildup"""
            suggestions = []
            pending_metrics = metric_store.get_metrics("automation.pending_tasks", start_time, end_time)
            
            if pending_metrics:
                avg_pending = statistics.mean([m.value for m in pending_metrics])
                max_pending = max([m.value for m in pending_metrics])
                
                if avg_pending > 100 or max_pending > 500:
                    suggestions.append(OptimizationSuggestion(
                        title="Task Queue Buildup Detected",
                        description=f"Average pending tasks: {avg_pending:.0f}, Max: {max_pending:.0f}",
                        category="throughput",
                        impact_level="high",
                        confidence_score=0.9,
                        estimated_improvement="2-5x throughput increase",
                        implementation_effort="medium",
                        suggested_actions=[
                            "Increase worker thread pool size",
                            "Implement task prioritization",
                            "Add horizontal scaling",
                            "Optimize task processing pipeline"
                        ],
                        related_metrics=["automation.pending_tasks", "automation.active_tasks"]
                    ))
            
            return suggestions
        
        # Register default rules
        self.optimization_rules = [
            high_cpu_usage_rule,
            high_memory_usage_rule, 
            high_error_rate_rule,
            slow_execution_rule,
            queue_buildup_rule
        ]

class ReportGenerator:
    """
    Generates comprehensive performance reports
    """
    
    def __init__(self, metric_store: MetricStore, analyzer: OptimizationAnalyzer):
        self.metric_store = metric_store
        self.analyzer = analyzer
        self.logger = logging.getLogger(__name__)
        
        # Report templates
        self.report_templates = {
            "daily": self._generate_daily_report,
            "weekly": self._generate_weekly_report,
            "monthly": self._generate_monthly_report,
            "custom": self._generate_custom_report
        }
    
    def generate_report(self, report_type: str = "daily", 
                       start_time: datetime = None, end_time: datetime = None) -> PerformanceReport:
        """Generate performance report"""
        if report_type not in self.report_templates:
            raise ValueError(f"Unknown report type: {report_type}")
        
        return self.report_templates[report_type](start_time, end_time)
    
    def _generate_daily_report(self, start_time: datetime = None, 
                             end_time: datetime = None) -> PerformanceReport:
        """Generate daily performance report"""
        end_time = end_time or datetime.now()
        start_time = start_time or (end_time - timedelta(days=1))
        
        report = PerformanceReport(
            report_type="daily",
            period_start=start_time,
            period_end=end_time
        )
        
        # Get summary metrics
        report.summary_metrics = self._calculate_period_metrics(start_time, end_time)
        
        # Get trends
        report.execution_trends = self._calculate_execution_trends(start_time, end_time, timedelta(hours=1))
        report.resource_trends = self._calculate_resource_trends(start_time, end_time, timedelta(hours=1))
        
        # Error analysis
        report.error_analysis = self._analyze_errors(start_time, end_time)
        
        # Generate insights
        report.key_insights = self._generate_insights(report)
        
        # Get optimization suggestions
        report.optimization_suggestions = self.analyzer.analyze_performance(end_time - start_time)
        
        # Calculate performance score
        report.performance_score = self._calculate_performance_score(report)
        
        # Generate charts
        if VISUALIZATION_AVAILABLE:
            report.charts_generated = self._generate_charts(report)
        
        return report
    
    def _generate_weekly_report(self, start_time: datetime = None, 
                              end_time: datetime = None) -> PerformanceReport:
        """Generate weekly performance report"""
        end_time = end_time or datetime.now()
        start_time = start_time or (end_time - timedelta(weeks=1))
        
        # Similar to daily but with different aggregation intervals
        report = PerformanceReport(
            report_type="weekly",
            period_start=start_time,
            period_end=end_time
        )
        
        report.summary_metrics = self._calculate_period_metrics(start_time, end_time)
        report.execution_trends = self._calculate_execution_trends(start_time, end_time, timedelta(hours=6))
        report.resource_trends = self._calculate_resource_trends(start_time, end_time, timedelta(hours=6))
        report.error_analysis = self._analyze_errors(start_time, end_time)
        report.key_insights = self._generate_insights(report)
        report.optimization_suggestions = self.analyzer.analyze_performance(end_time - start_time)
        report.performance_score = self._calculate_performance_score(report)
        
        if VISUALIZATION_AVAILABLE:
            report.charts_generated = self._generate_charts(report)
        
        return report
    
    def _generate_monthly_report(self, start_time: datetime = None, 
                               end_time: datetime = None) -> PerformanceReport:
        """Generate monthly performance report"""
        end_time = end_time or datetime.now()
        start_time = start_time or (end_time - timedelta(days=30))
        
        # Similar to daily but with different aggregation intervals
        report = PerformanceReport(
            report_type="monthly",
            period_start=start_time,
            period_end=end_time
        )
        
        report.summary_metrics = self._calculate_period_metrics(start_time, end_time)
        report.execution_trends = self._calculate_execution_trends(start_time, end_time, timedelta(days=1))
        report.resource_trends = self._calculate_resource_trends(start_time, end_time, timedelta(days=1))
        report.error_analysis = self._analyze_errors(start_time, end_time)
        report.key_insights = self._generate_insights(report)
        report.optimization_suggestions = self.analyzer.analyze_performance(end_time - start_time)
        report.performance_score = self._calculate_performance_score(report)
        
        if VISUALIZATION_AVAILABLE:
            report.charts_generated = self._generate_charts(report)
        
        return report
    
    def _generate_custom_report(self, start_time: datetime = None, 
                              end_time: datetime = None) -> PerformanceReport:
        """Generate custom performance report"""
        return self._generate_daily_report(start_time, end_time)
    
    def _calculate_period_metrics(self, start_time: datetime, end_time: datetime) -> PerformanceMetrics:
        """Calculate aggregated metrics for time period"""
        metrics = PerformanceMetrics()
        
        # Get execution metrics
        execution_times = self.metric_store.get_metrics("automation.execution_time", start_time, end_time)
        successes = self.metric_store.get_metrics("automation.success", start_time, end_time)
        failures = self.metric_store.get_metrics("automation.failure", start_time, end_time)
        
        if execution_times:
            times = [m.value for m in execution_times]
            metrics.average_execution_time = statistics.mean(times)
            metrics.max_execution_time = max(times)
            metrics.min_execution_time = min(times)
        
        metrics.successful_executions = len(successes)
        metrics.failed_executions = len(failures)
        metrics.total_tasks_executed = metrics.successful_executions + metrics.failed_executions
        
        if metrics.total_tasks_executed > 0:
            metrics.success_rate_percent = (metrics.successful_executions / metrics.total_tasks_executed) * 100
            metrics.error_rate_percent = (metrics.failed_executions / metrics.total_tasks_executed) * 100
        
        # Calculate throughput
        period_hours = (end_time - start_time).total_seconds() / 3600
        if period_hours > 0:
            metrics.tasks_per_hour = metrics.total_tasks_executed / period_hours
            metrics.tasks_per_minute = metrics.tasks_per_hour / 60
        
        # Get resource usage
        cpu_metrics = self.metric_store.get_metrics("system.cpu_percent", start_time, end_time)
        memory_metrics = self.metric_store.get_metrics("system.memory_percent", start_time, end_time)
        
        if cpu_metrics:
            metrics.cpu_usage_percent = statistics.mean([m.value for m in cpu_metrics])
        
        if memory_metrics:
            memory_values = [m.value for m in memory_metrics]
            metrics.memory_usage_mb = statistics.mean(memory_values)
        
        return metrics
    
    def _calculate_execution_trends(self, start_time: datetime, end_time: datetime, 
                                  interval: timedelta) -> List[Dict[str, Any]]:
        """Calculate execution trends over time"""
        trends = []
        current_time = start_time
        
        while current_time < end_time:
            interval_end = min(current_time + interval, end_time)
            
            executions = self.metric_store.get_metrics("automation.executions", current_time, interval_end)
            successes = self.metric_store.get_metrics("automation.success", current_time, interval_end)
            failures = self.metric_store.get_metrics("automation.failure", current_time, interval_end)
            execution_times = self.metric_store.get_metrics("automation.execution_time", current_time, interval_end)
            
            trend_point = {
                'timestamp': current_time.isoformat(),
                'period_start': current_time.isoformat(),
                'period_end': interval_end.isoformat(),
                'total_executions': len(executions),
                'successful_executions': len(successes),
                'failed_executions': len(failures),
                'success_rate': (len(successes) / len(executions)) * 100 if executions else 0,
                'average_execution_time': statistics.mean([m.value for m in execution_times]) if execution_times else 0
            }
            
            trends.append(trend_point)
            current_time = interval_end
        
        return trends
    
    def _calculate_resource_trends(self, start_time: datetime, end_time: datetime, 
                                 interval: timedelta) -> List[Dict[str, Any]]:
        """Calculate resource usage trends over time"""
        trends = []
        current_time = start_time
        
        while current_time < end_time:
            interval_end = min(current_time + interval, end_time)
            
            cpu_metrics = self.metric_store.get_metrics("system.cpu_percent", current_time, interval_end)
            memory_metrics = self.metric_store.get_metrics("system.memory_percent", current_time, interval_end)
            
            trend_point = {
                'timestamp': current_time.isoformat(),
                'period_start': current_time.isoformat(),
                'period_end': interval_end.isoformat(),
                'cpu_usage_percent': statistics.mean([m.value for m in cpu_metrics]) if cpu_metrics else 0,
                'memory_usage_percent': statistics.mean([m.value for m in memory_metrics]) if memory_metrics else 0,
                'cpu_max': max([m.value for m in cpu_metrics]) if cpu_metrics else 0,
                'memory_max': max([m.value for m in memory_metrics]) if memory_metrics else 0
            }
            
            trends.append(trend_point)
            current_time = interval_end
        
        return trends
    
    def _analyze_errors(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Analyze error patterns"""
        errors = []
        
        failures = self.metric_store.get_metrics("automation.failure", start_time, end_time)
        timeouts = self.metric_store.get_metrics("automation.timeout", start_time, end_time)
        
        # Group errors by time periods
        error_analysis = {
            'total_failures': len(failures),
            'total_timeouts': len(timeouts),
            'failure_rate_per_hour': len(failures) / max(1, (end_time - start_time).total_seconds() / 3600),
            'common_error_patterns': []  # Would need more detailed error tracking
        }
        
        errors.append(error_analysis)
        return errors
    
    def _generate_insights(self, report: PerformanceReport) -> List[str]:
        """Generate key insights from report data"""
        insights = []
        metrics = report.summary_metrics
        
        # Performance insights
        if metrics.success_rate_percent > 95:
            insights.append(f"Excellent reliability with {metrics.success_rate_percent:.1f}% success rate")
        elif metrics.success_rate_percent < 80:
            insights.append(f"Poor reliability detected: {metrics.success_rate_percent:.1f}% success rate needs improvement")
        
        # Throughput insights
        if metrics.tasks_per_hour > 1000:
            insights.append(f"High throughput achieved: {metrics.tasks_per_hour:.0f} tasks/hour")
        elif metrics.tasks_per_hour < 100:
            insights.append(f"Low throughput detected: {metrics.tasks_per_hour:.0f} tasks/hour")
        
        # Resource insights
        if metrics.cpu_usage_percent > 80:
            insights.append(f"High CPU utilization: {metrics.cpu_usage_percent:.1f}% - consider optimization")
        
        # Response time insights
        if metrics.average_execution_time > 30:
            insights.append(f"Slow average response time: {metrics.average_execution_time:.1f}s")
        elif metrics.average_execution_time < 5:
            insights.append(f"Fast response times: {metrics.average_execution_time:.1f}s average")
        
        return insights
    
    def _calculate_performance_score(self, report: PerformanceReport) -> float:
        """Calculate overall performance score (0-100)"""
        metrics = report.summary_metrics
        score = 0.0
        
        # Success rate component (40% weight)
        if metrics.total_tasks_executed > 0:
            success_score = metrics.success_rate_percent * 0.4
            score += success_score
        
        # Response time component (30% weight)
        if metrics.average_execution_time > 0:
            # Normalize execution time (assume 10s is good, 60s is poor)
            time_score = max(0, 100 - (metrics.average_execution_time / 60 * 100)) * 0.3
            score += time_score
        
        # Resource efficiency component (20% weight)
        resource_score = max(0, 100 - metrics.cpu_usage_percent) * 0.2
        score += resource_score
        
        # Throughput component (10% weight)
        # Normalize based on expected throughput (assume 500 tasks/hour is good)
        throughput_score = min(100, (metrics.tasks_per_hour / 500) * 100) * 0.1
        score += throughput_score
        
        return min(100, max(0, score))
    
    def _generate_charts(self, report: PerformanceReport) -> List[str]:
        """Generate visualization charts"""
        charts = []
        
        if not VISUALIZATION_AVAILABLE:
            return charts
        
        try:
            # Create charts directory
            charts_dir = Path("user_data/analytics/charts")
            charts_dir.mkdir(parents=True, exist_ok=True)
            
            # Execution trends chart
            if report.execution_trends:
                timestamps = [datetime.fromisoformat(t['timestamp']) for t in report.execution_trends]
                success_rates = [t['success_rate'] for t in report.execution_trends]
                
                plt.figure(figsize=(12, 6))
                plt.plot(timestamps, success_rates, marker='o')
                plt.title('Success Rate Over Time')
                plt.xlabel('Time')
                plt.ylabel('Success Rate (%)')
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                chart_path = charts_dir / f"success_rate_{report.id}.png"
                plt.savefig(chart_path)
                plt.close()
                charts.append(str(chart_path))
            
            # Resource usage chart
            if report.resource_trends:
                timestamps = [datetime.fromisoformat(t['timestamp']) for t in report.resource_trends]
                cpu_usage = [t['cpu_usage_percent'] for t in report.resource_trends]
                memory_usage = [t['memory_usage_percent'] for t in report.resource_trends]
                
                plt.figure(figsize=(12, 6))
                plt.plot(timestamps, cpu_usage, label='CPU Usage (%)', marker='o')
                plt.plot(timestamps, memory_usage, label='Memory Usage (%)', marker='s')
                plt.title('Resource Usage Over Time')
                plt.xlabel('Time')
                plt.ylabel('Usage (%)')
                plt.legend()
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                chart_path = charts_dir / f"resource_usage_{report.id}.png"
                plt.savefig(chart_path)
                plt.close()
                charts.append(str(chart_path))
                
        except Exception as e:
            self.logger.error(f"Chart generation error: {e}")
        
        return charts

class AutomationAnalytics:
    """
    Main automation analytics system
    """
    
    def __init__(self, db_path: str = "user_data/automation_analytics.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.monitor = PerformanceMonitor()
        self.analyzer = OptimizationAnalyzer(self.monitor.metric_store)
        self.report_generator = ReportGenerator(self.monitor.metric_store, self.analyzer)
        
        # Analytics settings
        self.auto_reports_enabled = True
        self.report_schedule = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30)
        }
        
        # Initialize database
        self._init_database()
        
        # Start monitoring
        self.monitor.start_monitoring()
    
    def start(self):
        """Start analytics system"""
        self.monitor.start_monitoring()
        self.logger.info("Automation analytics started")
    
    def stop(self):
        """Stop analytics system"""
        self.monitor.stop_monitoring()
        self.logger.info("Automation analytics stopped")
    
    def record_automation_event(self, event_type: str, execution_time: float = None,
                               success: bool = True, metadata: Dict[str, Any] = None):
        """Record automation event for analytics"""
        timestamp = datetime.now()
        
        # Record basic metrics
        self.monitor.record_metric(f"automation.{event_type}.count", 1, metadata)
        
        if execution_time is not None:
            self.monitor.record_execution_time(f"automation.{event_type}", execution_time, success, metadata)
        
        if success:
            self.monitor.record_metric("automation.success", 1)
        else:
            self.monitor.record_metric("automation.failure", 1)
    
    def get_current_performance(self) -> PerformanceMetrics:
        """Get current performance snapshot"""
        return self.monitor.get_performance_snapshot()
    
    def generate_optimization_suggestions(self) -> List[OptimizationSuggestion]:
        """Get optimization suggestions"""
        return self.analyzer.analyze_performance()
    
    def generate_report(self, report_type: str = "daily") -> PerformanceReport:
        """Generate performance report"""
        return self.report_generator.generate_report(report_type)
    
    def add_custom_metric_collector(self, collector: Callable[[], List[MetricPoint]]):
        """Add custom metric collector"""
        self.monitor.add_custom_collector(collector)
    
    def set_performance_alert(self, metric_name: str, threshold_type: str, threshold_value: float,
                            callback: Callable[[AnalyticsAlert], None] = None):
        """Set performance alert threshold"""
        self.monitor.set_alert_threshold(metric_name, threshold_type, threshold_value)
        if callback:
            self.monitor.add_alert_callback(callback)
    
    def get_analytics_dashboard_data(self) -> Dict[str, Any]:
        """Get data for analytics dashboard"""
        current_metrics = self.get_current_performance()
        suggestions = self.generate_optimization_suggestions()
        
        # Get recent metrics for trends
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=6)
        
        recent_executions = self.monitor.metric_store.get_metrics("automation.executions", start_time, end_time)
        recent_cpu = self.monitor.metric_store.get_metrics("system.cpu_percent", start_time, end_time)
        
        return {
            'current_metrics': asdict(current_metrics),
            'optimization_suggestions': [asdict(s) for s in suggestions[:5]],
            'recent_execution_count': len(recent_executions),
            'average_cpu_usage': statistics.mean([m.value for m in recent_cpu]) if recent_cpu else 0,
            'system_health_score': self._calculate_system_health_score(current_metrics),
            'alerts_count': 0,  # Would need alert storage to implement
            'uptime_hours': (datetime.now() - datetime.now().replace(hour=0, minute=0, second=0)).total_seconds() / 3600
        }
    
    def _calculate_system_health_score(self, metrics: PerformanceMetrics) -> float:
        """Calculate overall system health score"""
        score = 100.0
        
        # Deduct for high error rate
        if metrics.error_rate_percent > 10:
            score -= metrics.error_rate_percent * 2
        
        # Deduct for high resource usage
        if metrics.cpu_usage_percent > 80:
            score -= (metrics.cpu_usage_percent - 80) * 2
        
        # Deduct for slow response times
        if metrics.average_execution_time > 30:
            score -= min(30, metrics.average_execution_time - 30)
        
        # Deduct for queue buildup
        if metrics.pending_tasks > 100:
            score -= min(20, (metrics.pending_tasks - 100) / 10)
        
        return max(0, min(100, score))
    
    def _init_database(self):
        """Initialize analytics database"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                # Reports table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS performance_reports (
                        id TEXT PRIMARY KEY,
                        report_type TEXT,
                        period_start TEXT,
                        period_end TEXT,
                        summary_metrics TEXT,
                        performance_score REAL,
                        generated_time TEXT,
                        report_data TEXT
                    )
                ''')
                
                # Optimization suggestions table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS optimization_suggestions (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        description TEXT,
                        category TEXT,
                        impact_level TEXT,
                        confidence_score REAL,
                        created_time TEXT,
                        implemented BOOLEAN DEFAULT 0
                    )
                ''')
                
        except Exception as e:
            self.logger.error(f"Analytics database initialization failed: {e}")


# Utility functions
def create_execution_time_collector(automation_system) -> Callable[[], List[MetricPoint]]:
    """Create collector for automation execution times"""
    def collector():
        metrics = []
        
        # This would integrate with your automation system to collect metrics
        # For now, return empty list
        return metrics
    
    return collector

def create_queue_metrics_collector(automation_system) -> Callable[[], List[MetricPoint]]:
    """Create collector for queue metrics"""
    def collector():
        metrics = []
        
        # Collect queue metrics from automation system
        # pending_tasks = automation_system.get_pending_task_count()
        # active_tasks = automation_system.get_active_task_count()
        
        # metrics.append(MetricPoint("automation.pending_tasks", pending_tasks))
        # metrics.append(MetricPoint("automation.active_tasks", active_tasks))
        
        return metrics
    
    return collector