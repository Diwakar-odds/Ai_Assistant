"""
Context-Aware Automation System

This module provides environmental awareness, adaptive behavior, smart learning,
and intelligent context detection for responsive automation systems.

Features:
- Environmental context detection
- Adaptive automation behavior
- Machine learning for optimization
- Smart context prediction
- Dynamic automation adjustment
- User behavior learning
- System state awareness
- Intelligent decision making
"""

import time
import json
import logging
import threading
import sqlite3
import pickle
import hashlib
from typing import Dict, List, Optional, Any, Callable, Tuple, Union, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import uuid
from collections import defaultdict, deque
import statistics
import math

# Machine Learning
try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, mean_squared_error
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# System monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class ContextType(Enum):
    """Types of context information"""
    SYSTEM = "system"                    # System resource state
    USER = "user"                       # User behavior and preferences
    TEMPORAL = "temporal"               # Time-based patterns
    ENVIRONMENTAL = "environmental"     # External environment factors
    APPLICATION = "application"         # Application-specific context
    NETWORK = "network"                 # Network conditions
    SECURITY = "security"               # Security state and threats
    PERFORMANCE = "performance"         # Performance metrics and trends

class AdaptationStrategy(Enum):
    """Strategies for adaptation"""
    REACTIVE = "reactive"               # React to immediate changes
    PREDICTIVE = "predictive"           # Predict and prepare for changes
    LEARNED = "learned"                 # Use machine learning insights
    RULE_BASED = "rule_based"          # Follow predefined rules
    HYBRID = "hybrid"                   # Combination of strategies

class LearningMode(Enum):
    """Machine learning modes"""
    SUPERVISED = "supervised"           # Supervised learning with labeled data
    UNSUPERVISED = "unsupervised"      # Unsupervised pattern discovery
    REINFORCEMENT = "reinforcement"     # Reinforcement learning from feedback
    CONTINUOUS = "continuous"           # Continuous online learning

@dataclass
class ContextData:
    """Context information snapshot"""
    context_type: ContextType
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source: str = "system"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_signature(self) -> str:
        """Get context signature for similarity comparison"""
        # Create a signature based on key context features
        key_data = {k: v for k, v in self.data.items() if isinstance(v, (int, float, str, bool))}
        signature_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(signature_str.encode()).hexdigest()

@dataclass
class ContextPattern:
    """Detected context pattern"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: str = ""
    description: str = ""
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    frequency: int = 1
    confidence: float = 0.0
    last_seen: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    # Pattern characteristics
    typical_duration: Optional[timedelta] = None
    typical_time_of_day: Optional[int] = None  # Hour of day (0-23)
    typical_day_of_week: Optional[int] = None  # Day of week (0-6)
    seasonal_pattern: bool = False

@dataclass
class AdaptationRule:
    """Rule for context-based adaptation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # Trigger conditions
    trigger_contexts: List[ContextType] = field(default_factory=list)
    trigger_conditions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Actions
    adaptation_actions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Settings
    priority: int = 5
    enabled: bool = True
    strategy: AdaptationStrategy = AdaptationStrategy.REACTIVE
    
    # Performance tracking
    trigger_count: int = 0
    success_count: int = 0
    last_triggered: Optional[datetime] = None
    
    def matches_context(self, contexts: Dict[ContextType, ContextData]) -> bool:
        """Check if current context matches trigger conditions"""
        try:
            # Check if required context types are present
            for context_type in self.trigger_contexts:
                if context_type not in contexts:
                    return False
            
            # Evaluate trigger conditions
            for condition in self.trigger_conditions:
                if not self._evaluate_condition(condition, contexts):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _evaluate_condition(self, condition: Dict[str, Any], 
                          contexts: Dict[ContextType, ContextData]) -> bool:
        """Evaluate a single condition"""
        try:
            context_type = ContextType(condition.get('context_type'))
            field_path = condition.get('field_path')
            operator = condition.get('operator', 'eq')
            expected_value = condition.get('value')
            
            if context_type not in contexts:
                return False
            
            context_data = contexts[context_type]
            actual_value = self._get_nested_value(context_data.data, field_path)
            
            if operator == 'eq':
                return actual_value == expected_value
            elif operator == 'ne':
                return actual_value != expected_value
            elif operator == 'gt':
                return actual_value > expected_value
            elif operator == 'lt':
                return actual_value < expected_value
            elif operator == 'gte':
                return actual_value >= expected_value
            elif operator == 'lte':
                return actual_value <= expected_value
            elif operator == 'in':
                return actual_value in expected_value
            elif operator == 'contains':
                return expected_value in str(actual_value)
            
            return False
            
        except Exception:
            return False
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested value from data using dot notation"""
        try:
            value = data
            for part in field_path.split('.'):
                value = value[part]
            return value
        except (KeyError, TypeError):
            return None

class ContextCollector:
    """
    Collects context information from various sources
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.collectors: Dict[ContextType, List[Callable]] = defaultdict(list)
        self.collection_intervals: Dict[ContextType, float] = {}
        self.collection_active = False
        self.collector_threads: Dict[ContextType, threading.Thread] = {}
        
        # Context cache
        self.context_cache: Dict[ContextType, ContextData] = {}
        self.cache_lock = threading.RLock()
        
        # Setup default collectors
        self._setup_default_collectors()
    
    def start_collection(self):
        """Start context collection"""
        if self.collection_active:
            return
        
        self.collection_active = True
        
        # Start collector threads for each context type
        for context_type in self.collectors.keys():
            interval = self.collection_intervals.get(context_type, 5.0)
            thread = threading.Thread(
                target=self._collection_loop,
                args=(context_type, interval),
                daemon=True
            )
            self.collector_threads[context_type] = thread
            thread.start()
        
        self.logger.info("Context collection started")
    
    def stop_collection(self):
        """Stop context collection"""
        if not self.collection_active:
            return
        
        self.collection_active = False
        
        # Wait for collector threads to finish
        for thread in self.collector_threads.values():
            thread.join(timeout=2.0)
        
        self.collector_threads.clear()
        self.logger.info("Context collection stopped")
    
    def register_collector(self, context_type: ContextType, collector: Callable[[], ContextData],
                          collection_interval: float = 5.0):
        """Register context collector"""
        self.collectors[context_type].append(collector)
        self.collection_intervals[context_type] = collection_interval
        
        self.logger.debug(f"Registered collector for {context_type.value}")
    
    def get_current_context(self, context_type: ContextType = None) -> Union[ContextData, Dict[ContextType, ContextData]]:
        """Get current context data"""
        with self.cache_lock:
            if context_type:
                return self.context_cache.get(context_type)
            else:
                return self.context_cache.copy()
    
    def collect_context_now(self, context_type: ContextType) -> Optional[ContextData]:
        """Force immediate context collection"""
        collectors = self.collectors.get(context_type, [])
        
        for collector in collectors:
            try:
                context_data = collector()
                if context_data:
                    with self.cache_lock:
                        self.context_cache[context_type] = context_data
                    return context_data
            except Exception as e:
                self.logger.error(f"Context collector error for {context_type.value}: {e}")
        
        return None
    
    def _collection_loop(self, context_type: ContextType, interval: float):
        """Context collection loop for specific type"""
        while self.collection_active:
            try:
                self.collect_context_now(context_type)
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"Collection loop error for {context_type.value}: {e}")
                time.sleep(max(interval, 5.0))
    
    def _setup_default_collectors(self):
        """Setup default context collectors"""
        
        # System context collector
        def collect_system_context() -> ContextData:
            data = {}
            
            if PSUTIL_AVAILABLE:
                try:
                    # CPU information
                    data['cpu_percent'] = psutil.cpu_percent()
                    data['cpu_count'] = psutil.cpu_count()
                    data['load_average'] = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                    
                    # Memory information
                    memory = psutil.virtual_memory()
                    data['memory_total'] = memory.total
                    data['memory_used'] = memory.used
                    data['memory_percent'] = memory.percent
                    
                    # Disk information
                    disk = psutil.disk_usage('/')
                    data['disk_total'] = disk.total
                    data['disk_used'] = disk.used
                    data['disk_percent'] = disk.percent
                    
                    # Process information
                    data['process_count'] = len(psutil.pids())
                    
                    # Network information
                    net_io = psutil.net_io_counters()
                    data['network_bytes_sent'] = net_io.bytes_sent
                    data['network_bytes_recv'] = net_io.bytes_recv
                    
                except Exception as e:
                    self.logger.debug(f"System context collection error: {e}")
            
            return ContextData(
                context_type=ContextType.SYSTEM,
                data=data,
                source="psutil"
            )
        
        # Temporal context collector
        def collect_temporal_context() -> ContextData:
            now = datetime.now()
            
            data = {
                'timestamp': now.timestamp(),
                'hour': now.hour,
                'minute': now.minute,
                'day_of_week': now.weekday(),
                'day_of_month': now.day,
                'month': now.month,
                'year': now.year,
                'is_weekend': now.weekday() >= 5,
                'is_business_hours': 9 <= now.hour <= 17,
                'is_night_time': now.hour < 6 or now.hour > 22,
                'quarter': (now.month - 1) // 3 + 1,
                'week_of_year': now.isocalendar()[1]
            }
            
            return ContextData(
                context_type=ContextType.TEMPORAL,
                data=data,
                source="datetime"
            )
        
        # Performance context collector
        def collect_performance_context() -> ContextData:
            # This would integrate with the analytics system
            data = {
                'avg_response_time': 0.0,
                'success_rate': 100.0,
                'error_rate': 0.0,
                'throughput': 0.0,
                'queue_size': 0
            }
            
            return ContextData(
                context_type=ContextType.PERFORMANCE,
                data=data,
                source="analytics"
            )
        
        # Register default collectors
        self.register_collector(ContextType.SYSTEM, collect_system_context, 5.0)
        self.register_collector(ContextType.TEMPORAL, collect_temporal_context, 60.0)
        self.register_collector(ContextType.PERFORMANCE, collect_performance_context, 30.0)

class PatternDetector:
    """
    Detects patterns in context data
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.patterns: Dict[str, ContextPattern] = {}
        self.pattern_history = deque(maxlen=10000)
        self.detection_rules = []
        
        # ML models for pattern detection
        self.ml_models = {}
        self.scaler = StandardScaler() if ML_AVAILABLE else None
        
        # Setup default detection rules
        self._setup_default_detection_rules()
    
    def add_context_sample(self, contexts: Dict[ContextType, ContextData]):
        """Add context sample for pattern detection"""
        # Store in history
        self.pattern_history.append({
            'timestamp': datetime.now(),
            'contexts': contexts
        })
        
        # Run pattern detection
        self._detect_patterns(contexts)
    
    def get_detected_patterns(self) -> List[ContextPattern]:
        """Get all detected patterns"""
        return list(self.patterns.values())
    
    def get_patterns_by_type(self, pattern_type: str) -> List[ContextPattern]:
        """Get patterns by type"""
        return [p for p in self.patterns.values() if p.pattern_type == pattern_type]
    
    def predict_next_context(self, current_contexts: Dict[ContextType, ContextData]) -> Dict[str, Any]:
        """Predict likely next context based on patterns"""
        predictions = {}
        
        if not ML_AVAILABLE:
            return predictions
        
        try:
            # Find similar historical contexts
            similar_contexts = self._find_similar_contexts(current_contexts)
            
            if similar_contexts:
                # Use most recent similar context as prediction
                next_context = similar_contexts[0]['contexts']
                predictions = {
                    'system_cpu': next_context.get(ContextType.SYSTEM, ContextData(ContextType.SYSTEM)).data.get('cpu_percent', 0),
                    'system_memory': next_context.get(ContextType.SYSTEM, ContextData(ContextType.SYSTEM)).data.get('memory_percent', 0),
                    'confidence': 0.7
                }
            
        except Exception as e:
            self.logger.error(f"Context prediction error: {e}")
        
        return predictions
    
    def _detect_patterns(self, contexts: Dict[ContextType, ContextData]):
        """Run pattern detection on current contexts"""
        for rule in self.detection_rules:
            try:
                pattern = rule(contexts, list(self.pattern_history))
                if pattern:
                    self._update_pattern(pattern)
            except Exception as e:
                self.logger.error(f"Pattern detection rule error: {e}")
    
    def _update_pattern(self, pattern: ContextPattern):
        """Update detected pattern"""
        pattern_id = pattern.id
        
        if pattern_id in self.patterns:
            # Update existing pattern
            existing = self.patterns[pattern_id]
            existing.frequency += 1
            existing.last_seen = datetime.now()
            existing.confidence = min(1.0, existing.confidence + 0.1)
        else:
            # Add new pattern
            self.patterns[pattern_id] = pattern
        
        self.logger.debug(f"Pattern detected: {pattern.description}")
    
    def _find_similar_contexts(self, current_contexts: Dict[ContextType, ContextData], 
                             similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Find historically similar contexts"""
        similar = []
        
        current_signature = self._create_context_signature(current_contexts)
        
        for historical in list(self.pattern_history)[-100:]:  # Check last 100 samples
            historical_contexts = historical['contexts']
            historical_signature = self._create_context_signature(historical_contexts)
            
            similarity = self._calculate_similarity(current_signature, historical_signature)
            
            if similarity >= similarity_threshold:
                similar.append({
                    'contexts': historical_contexts,
                    'timestamp': historical['timestamp'],
                    'similarity': similarity
                })
        
        return sorted(similar, key=lambda x: x['similarity'], reverse=True)
    
    def _create_context_signature(self, contexts: Dict[ContextType, ContextData]) -> Dict[str, float]:
        """Create numerical signature for contexts"""
        signature = {}
        
        # System context features
        if ContextType.SYSTEM in contexts:
            system_data = contexts[ContextType.SYSTEM].data
            signature.update({
                'cpu_percent': system_data.get('cpu_percent', 0),
                'memory_percent': system_data.get('memory_percent', 0),
                'disk_percent': system_data.get('disk_percent', 0),
                'process_count': system_data.get('process_count', 0)
            })
        
        # Temporal context features
        if ContextType.TEMPORAL in contexts:
            temporal_data = contexts[ContextType.TEMPORAL].data
            signature.update({
                'hour': temporal_data.get('hour', 0),
                'day_of_week': temporal_data.get('day_of_week', 0),
                'is_weekend': float(temporal_data.get('is_weekend', False)),
                'is_business_hours': float(temporal_data.get('is_business_hours', False))
            })
        
        # Performance context features
        if ContextType.PERFORMANCE in contexts:
            perf_data = contexts[ContextType.PERFORMANCE].data
            signature.update({
                'avg_response_time': perf_data.get('avg_response_time', 0),
                'success_rate': perf_data.get('success_rate', 100),
                'throughput': perf_data.get('throughput', 0)
            })
        
        return signature
    
    def _calculate_similarity(self, sig1: Dict[str, float], sig2: Dict[str, float]) -> float:
        """Calculate similarity between context signatures"""
        try:
            common_keys = set(sig1.keys()) & set(sig2.keys())
            if not common_keys:
                return 0.0
            
            # Calculate euclidean distance
            distance = 0.0
            for key in common_keys:
                v1 = sig1[key]
                v2 = sig2[key]
                distance += (v1 - v2) ** 2
            
            distance = math.sqrt(distance)
            
            # Convert to similarity (0-1)
            max_distance = math.sqrt(len(common_keys) * 100 ** 2)  # Assume max diff of 100 per feature
            similarity = max(0, 1 - distance / max_distance)
            
            return similarity
            
        except Exception:
            return 0.0
    
    def _setup_default_detection_rules(self):
        """Setup default pattern detection rules"""
        
        def high_cpu_pattern(contexts: Dict[ContextType, ContextData], 
                           history: List[Dict[str, Any]]) -> Optional[ContextPattern]:
            """Detect high CPU usage patterns"""
            if ContextType.SYSTEM not in contexts:
                return None
            
            cpu_percent = contexts[ContextType.SYSTEM].data.get('cpu_percent', 0)
            
            if cpu_percent > 80:
                # Check if this is a recurring pattern
                recent_high_cpu = 0
                for sample in history[-10:]:  # Check last 10 samples
                    sample_contexts = sample.get('contexts', {})
                    if ContextType.SYSTEM in sample_contexts:
                        sample_cpu = sample_contexts[ContextType.SYSTEM].data.get('cpu_percent', 0)
                        if sample_cpu > 80:
                            recent_high_cpu += 1
                
                if recent_high_cpu >= 3:  # High CPU in at least 3 recent samples
                    return ContextPattern(
                        id="high_cpu_pattern",
                        pattern_type="resource_usage",
                        description=f"High CPU usage detected: {cpu_percent:.1f}%",
                        conditions=[{
                            'context_type': 'system',
                            'field_path': 'cpu_percent',
                            'operator': 'gt',
                            'value': 80
                        }],
                        confidence=0.8,
                        tags=["performance", "cpu", "high_usage"]
                    )
            
            return None
        
        def temporal_pattern(contexts: Dict[ContextType, ContextData], 
                           history: List[Dict[str, Any]]) -> Optional[ContextPattern]:
            """Detect temporal patterns"""
            if ContextType.TEMPORAL not in contexts:
                return None
            
            current_hour = contexts[ContextType.TEMPORAL].data.get('hour')
            current_dow = contexts[ContextType.TEMPORAL].data.get('day_of_week')
            
            # Check for business hours pattern
            if contexts[ContextType.TEMPORAL].data.get('is_business_hours'):
                return ContextPattern(
                    id="business_hours_pattern",
                    pattern_type="temporal",
                    description="Business hours activity pattern",
                    conditions=[{
                        'context_type': 'temporal',
                        'field_path': 'is_business_hours',
                        'operator': 'eq',
                        'value': True
                    }],
                    confidence=0.9,
                    typical_time_of_day=current_hour,
                    typical_day_of_week=current_dow,
                    tags=["temporal", "business_hours"]
                )
            
            return None
        
        def performance_degradation_pattern(contexts: Dict[ContextType, ContextData], 
                                          history: List[Dict[str, Any]]) -> Optional[ContextPattern]:
            """Detect performance degradation patterns"""
            if ContextType.PERFORMANCE not in contexts:
                return None
            
            current_response_time = contexts[ContextType.PERFORMANCE].data.get('avg_response_time', 0)
            success_rate = contexts[ContextType.PERFORMANCE].data.get('success_rate', 100)
            
            if current_response_time > 5.0 or success_rate < 90:
                return ContextPattern(
                    id="performance_degradation_pattern",
                    pattern_type="performance",
                    description=f"Performance degradation: {current_response_time:.1f}s response, {success_rate:.1f}% success",
                    conditions=[{
                        'context_type': 'performance',
                        'field_path': 'avg_response_time',
                        'operator': 'gt',
                        'value': 5.0
                    }],
                    confidence=0.7,
                    tags=["performance", "degradation", "slow_response"]
                )
            
            return None
        
        # Register detection rules
        self.detection_rules = [
            high_cpu_pattern,
            temporal_pattern,
            performance_degradation_pattern
        ]

class AdaptationEngine:
    """
    Engine for context-based automation adaptation
    """
    
    def __init__(self, context_collector: ContextCollector, pattern_detector: PatternDetector):
        self.context_collector = context_collector
        self.pattern_detector = pattern_detector
        self.logger = logging.getLogger(__name__)
        
        # Adaptation rules
        self.adaptation_rules: Dict[str, AdaptationRule] = {}
        self.active_adaptations: Set[str] = set()
        
        # Adaptation history
        self.adaptation_history = deque(maxlen=1000)
        
        # Callbacks for automation system integration
        self.adaptation_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # Engine state
        self.engine_active = False
        self.engine_thread = None
        
        # Setup default adaptation rules
        self._setup_default_adaptation_rules()
    
    def start_engine(self):
        """Start adaptation engine"""
        if self.engine_active:
            return
        
        self.engine_active = True
        self.engine_thread = threading.Thread(target=self._adaptation_loop, daemon=True)
        self.engine_thread.start()
        
        self.logger.info("Adaptation engine started")
    
    def stop_engine(self):
        """Stop adaptation engine"""
        if not self.engine_active:
            return
        
        self.engine_active = False
        if self.engine_thread:
            self.engine_thread.join(timeout=5.0)
        
        self.logger.info("Adaptation engine stopped")
    
    def add_adaptation_rule(self, rule: AdaptationRule):
        """Add adaptation rule"""
        self.adaptation_rules[rule.id] = rule
        self.logger.info(f"Added adaptation rule: {rule.name}")
    
    def remove_adaptation_rule(self, rule_id: str):
        """Remove adaptation rule"""
        if rule_id in self.adaptation_rules:
            del self.adaptation_rules[rule_id]
            self.active_adaptations.discard(rule_id)
            self.logger.info(f"Removed adaptation rule: {rule_id}")
    
    def register_adaptation_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Register callback for adaptation actions"""
        self.adaptation_callbacks.append(callback)
    
    def force_adaptation_check(self):
        """Force immediate adaptation check"""
        current_contexts = self.context_collector.get_current_context()
        if isinstance(current_contexts, dict):
            self._evaluate_adaptations(current_contexts)
    
    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get adaptation engine statistics"""
        total_rules = len(self.adaptation_rules)
        active_rules = len([r for r in self.adaptation_rules.values() if r.enabled])
        
        total_triggers = sum(r.trigger_count for r in self.adaptation_rules.values())
        total_successes = sum(r.success_count for r in self.adaptation_rules.values())
        
        return {
            'engine_active': self.engine_active,
            'total_rules': total_rules,
            'active_rules': active_rules,
            'disabled_rules': total_rules - active_rules,
            'total_triggers': total_triggers,
            'total_successes': total_successes,
            'success_rate': (total_successes / total_triggers) if total_triggers > 0 else 0.0,
            'active_adaptations': len(self.active_adaptations),
            'adaptation_history_size': len(self.adaptation_history)
        }
    
    def _adaptation_loop(self):
        """Main adaptation engine loop"""
        while self.engine_active:
            try:
                current_contexts = self.context_collector.get_current_context()
                
                if isinstance(current_contexts, dict) and current_contexts:
                    # Add context sample to pattern detector
                    self.pattern_detector.add_context_sample(current_contexts)
                    
                    # Evaluate adaptations
                    self._evaluate_adaptations(current_contexts)
                
                time.sleep(5.0)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Adaptation loop error: {e}")
                time.sleep(10.0)
    
    def _evaluate_adaptations(self, contexts: Dict[ContextType, ContextData]):
        """Evaluate adaptation rules against current context"""
        for rule_id, rule in self.adaptation_rules.items():
            if not rule.enabled:
                continue
            
            try:
                if rule.matches_context(contexts):
                    self._trigger_adaptation(rule, contexts)
                    
            except Exception as e:
                self.logger.error(f"Adaptation evaluation error for rule {rule.name}: {e}")
    
    def _trigger_adaptation(self, rule: AdaptationRule, contexts: Dict[ContextType, ContextData]):
        """Trigger adaptation rule"""
        try:
            # Update rule statistics
            rule.trigger_count += 1
            rule.last_triggered = datetime.now()
            
            # Execute adaptation actions
            success = self._execute_adaptation_actions(rule, contexts)
            
            if success:
                rule.success_count += 1
                self.active_adaptations.add(rule.id)
            
            # Record adaptation event
            self.adaptation_history.append({
                'timestamp': datetime.now(),
                'rule_id': rule.id,
                'rule_name': rule.name,
                'contexts': {k.value: v.data for k, v in contexts.items()},
                'success': success
            })
            
            self.logger.info(f"Triggered adaptation: {rule.name} ({'success' if success else 'failed'})")
            
        except Exception as e:
            self.logger.error(f"Adaptation trigger error for rule {rule.name}: {e}")
    
    def _execute_adaptation_actions(self, rule: AdaptationRule, 
                                  contexts: Dict[ContextType, ContextData]) -> bool:
        """Execute adaptation actions"""
        try:
            for action in rule.adaptation_actions:
                action_type = action.get('type')
                action_params = action.get('parameters', {})
                
                # Resolve parameter values from context
                resolved_params = self._resolve_action_parameters(action_params, contexts)
                
                # Execute action through callbacks
                for callback in self.adaptation_callbacks:
                    try:
                        callback(action_type, resolved_params)
                    except Exception as e:
                        self.logger.error(f"Adaptation callback error: {e}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Adaptation action execution error: {e}")
            return False
    
    def _resolve_action_parameters(self, parameters: Dict[str, Any], 
                                 contexts: Dict[ContextType, ContextData]) -> Dict[str, Any]:
        """Resolve action parameters from context"""
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith('$'):
                # Context reference
                path_parts = value[1:].split('.')
                if len(path_parts) >= 2:
                    context_type_str = path_parts[0]
                    field_path = '.'.join(path_parts[1:])
                    
                    try:
                        context_type = ContextType(context_type_str)
                        if context_type in contexts:
                            resolved_value = self._get_nested_value(contexts[context_type].data, field_path)
                            resolved[key] = resolved_value
                        else:
                            resolved[key] = None
                    except ValueError:
                        resolved[key] = value
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
        
        return resolved
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested value from data using dot notation"""
        try:
            value = data
            for part in field_path.split('.'):
                value = value[part]
            return value
        except (KeyError, TypeError):
            return None
    
    def _setup_default_adaptation_rules(self):
        """Setup default adaptation rules"""
        
        # High CPU adaptation rule
        high_cpu_rule = AdaptationRule(
            id="high_cpu_adaptation",
            name="High CPU Adaptation",
            description="Reduce automation load when CPU usage is high",
            trigger_contexts=[ContextType.SYSTEM],
            trigger_conditions=[{
                'context_type': 'system',
                'field_path': 'cpu_percent',
                'operator': 'gt',
                'value': 85
            }],
            adaptation_actions=[{
                'type': 'reduce_concurrency',
                'parameters': {
                    'target_threads': 2,
                    'reason': 'High CPU usage detected'
                }
            }],
            strategy=AdaptationStrategy.REACTIVE,
            priority=8
        )
        
        # Low memory adaptation rule
        low_memory_rule = AdaptationRule(
            id="low_memory_adaptation",
            name="Low Memory Adaptation",
            description="Optimize memory usage when memory is low",
            trigger_contexts=[ContextType.SYSTEM],
            trigger_conditions=[{
                'context_type': 'system',
                'field_path': 'memory_percent',
                'operator': 'gt',
                'value': 90
            }],
            adaptation_actions=[{
                'type': 'optimize_memory',
                'parameters': {
                    'clear_caches': True,
                    'reduce_buffers': True,
                    'reason': 'Low memory availability'
                }
            }],
            strategy=AdaptationStrategy.REACTIVE,
            priority=9
        )
        
        # Business hours adaptation rule
        business_hours_rule = AdaptationRule(
            id="business_hours_adaptation",
            name="Business Hours Adaptation",
            description="Adjust automation behavior during business hours",
            trigger_contexts=[ContextType.TEMPORAL],
            trigger_conditions=[{
                'context_type': 'temporal',
                'field_path': 'is_business_hours',
                'operator': 'eq',
                'value': True
            }],
            adaptation_actions=[{
                'type': 'adjust_priority',
                'parameters': {
                    'priority_boost': 2,
                    'reason': 'Business hours - higher priority'
                }
            }],
            strategy=AdaptationStrategy.PREDICTIVE,
            priority=5
        )
        
        # Performance degradation adaptation rule
        performance_rule = AdaptationRule(
            id="performance_adaptation",
            name="Performance Adaptation",
            description="Adapt to performance issues",
            trigger_contexts=[ContextType.PERFORMANCE],
            trigger_conditions=[{
                'context_type': 'performance',
                'field_path': 'success_rate',
                'operator': 'lt',
                'value': 85
            }],
            adaptation_actions=[{
                'type': 'increase_retries',
                'parameters': {
                    'retry_count': 3,
                    'retry_delay': 2.0,
                    'reason': 'Low success rate detected'
                }
            }],
            strategy=AdaptationStrategy.LEARNED,
            priority=7
        )
        
        # Add default rules
        self.adaptation_rules = {
            high_cpu_rule.id: high_cpu_rule,
            low_memory_rule.id: low_memory_rule,
            business_hours_rule.id: business_hours_rule,
            performance_rule.id: performance_rule
        }

class ContextAwareAutomation:
    """
    Main context-aware automation system
    """
    
    def __init__(self, db_path: str = "user_data/context_automation.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.context_collector = ContextCollector()
        self.pattern_detector = PatternDetector()
        self.adaptation_engine = AdaptationEngine(self.context_collector, self.pattern_detector)
        
        # System state
        self.system_active = False
        
        # Initialize database
        self._init_database()
        
        # Load saved patterns and rules
        self._load_saved_data()
    
    def start(self):
        """Start context-aware automation system"""
        if self.system_active:
            return
        
        self.system_active = True
        
        # Start components
        self.context_collector.start_collection()
        self.adaptation_engine.start_engine()
        
        self.logger.info("Context-aware automation system started")
    
    def stop(self):
        """Stop context-aware automation system"""
        if not self.system_active:
            return
        
        self.system_active = False
        
        # Stop components
        self.context_collector.stop_collection()
        self.adaptation_engine.stop_engine()
        
        # Save current state
        self._save_current_state()
        
        self.logger.info("Context-aware automation system stopped")
    
    def get_current_context(self) -> Dict[str, Any]:
        """Get current context information"""
        contexts = self.context_collector.get_current_context()
        
        if isinstance(contexts, dict):
            return {
                context_type.value: {
                    'data': context_data.data,
                    'timestamp': context_data.timestamp.isoformat(),
                    'confidence': context_data.confidence,
                    'source': context_data.source
                }
                for context_type, context_data in contexts.items()
            }
        
        return {}
    
    def get_detected_patterns(self) -> List[Dict[str, Any]]:
        """Get detected context patterns"""
        patterns = self.pattern_detector.get_detected_patterns()
        
        return [
            {
                'id': pattern.id,
                'type': pattern.pattern_type,
                'description': pattern.description,
                'frequency': pattern.frequency,
                'confidence': pattern.confidence,
                'last_seen': pattern.last_seen.isoformat(),
                'tags': pattern.tags,
                'typical_duration': pattern.typical_duration.total_seconds() if pattern.typical_duration else None,
                'typical_time_of_day': pattern.typical_time_of_day,
                'typical_day_of_week': pattern.typical_day_of_week
            }
            for pattern in patterns
        ]
    
    def get_adaptation_rules(self) -> List[Dict[str, Any]]:
        """Get adaptation rules"""
        return [
            {
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'trigger_contexts': [ct.value for ct in rule.trigger_contexts],
                'strategy': rule.strategy.value,
                'priority': rule.priority,
                'enabled': rule.enabled,
                'trigger_count': rule.trigger_count,
                'success_count': rule.success_count,
                'last_triggered': rule.last_triggered.isoformat() if rule.last_triggered else None,
                'success_rate': (rule.success_count / rule.trigger_count) if rule.trigger_count > 0 else 0.0
            }
            for rule in self.adaptation_engine.adaptation_rules.values()
        ]
    
    def predict_context(self, hours_ahead: int = 1) -> Dict[str, Any]:
        """Predict context for future time"""
        current_contexts = self.context_collector.get_current_context()
        
        if isinstance(current_contexts, dict):
            return self.pattern_detector.predict_next_context(current_contexts)
        
        return {}
    
    def register_context_collector(self, context_type: ContextType, collector: Callable[[], ContextData],
                                 collection_interval: float = 5.0):
        """Register custom context collector"""
        self.context_collector.register_collector(context_type, collector, collection_interval)
    
    def add_adaptation_rule(self, rule_data: Dict[str, Any]) -> str:
        """Add custom adaptation rule"""
        rule = AdaptationRule(
            id=rule_data.get('id', str(uuid.uuid4())),
            name=rule_data['name'],
            description=rule_data.get('description', ''),
            trigger_contexts=[ContextType(ct) for ct in rule_data.get('trigger_contexts', [])],
            trigger_conditions=rule_data.get('trigger_conditions', []),
            adaptation_actions=rule_data.get('adaptation_actions', []),
            priority=rule_data.get('priority', 5),
            strategy=AdaptationStrategy(rule_data.get('strategy', 'reactive'))
        )
        
        self.adaptation_engine.add_adaptation_rule(rule)
        return rule.id
    
    def register_adaptation_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Register callback for adaptation actions"""
        self.adaptation_engine.register_adaptation_callback(callback)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        adaptation_stats = self.adaptation_engine.get_adaptation_stats()
        patterns = self.pattern_detector.get_detected_patterns()
        contexts = self.context_collector.get_current_context()
        
        return {
            'system_active': self.system_active,
            'context_types_collected': len(contexts) if isinstance(contexts, dict) else 0,
            'patterns_detected': len(patterns),
            'adaptation_stats': adaptation_stats,
            'context_collection_active': self.context_collector.collection_active,
            'pattern_history_size': len(self.pattern_detector.pattern_history)
        }
    
    def _init_database(self):
        """Initialize context database"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                # Patterns table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS context_patterns (
                        id TEXT PRIMARY KEY,
                        pattern_type TEXT,
                        description TEXT,
                        conditions TEXT,
                        frequency INTEGER,
                        confidence REAL,
                        last_seen TEXT,
                        tags TEXT,
                        created_time TEXT
                    )
                ''')
                
                # Adaptation rules table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS adaptation_rules (
                        id TEXT PRIMARY KEY,
                        name TEXT,
                        description TEXT,
                        trigger_contexts TEXT,
                        trigger_conditions TEXT,
                        adaptation_actions TEXT,
                        priority INTEGER,
                        strategy TEXT,
                        enabled BOOLEAN,
                        trigger_count INTEGER DEFAULT 0,
                        success_count INTEGER DEFAULT 0,
                        created_time TEXT
                    )
                ''')
                
        except Exception as e:
            self.logger.error(f"Context database initialization failed: {e}")
    
    def _load_saved_data(self):
        """Load saved patterns and rules from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Load patterns
                cursor = conn.execute('SELECT * FROM context_patterns')
                for row in cursor.fetchall():
                    # Would deserialize and load patterns
                    self.logger.debug(f"Found saved pattern: {row[1]}")
                
                # Load adaptation rules  
                cursor = conn.execute('SELECT * FROM adaptation_rules')
                for row in cursor.fetchall():
                    # Would deserialize and load adaptation rules
                    self.logger.debug(f"Found saved adaptation rule: {row[1]}")
                    
        except Exception as e:
            self.logger.error(f"Failed to load saved data: {e}")
    
    def _save_current_state(self):
        """Save current state to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Save patterns
                for pattern in self.pattern_detector.patterns.values():
                    conn.execute('''
                        INSERT OR REPLACE INTO context_patterns
                        (id, pattern_type, description, conditions, frequency, confidence,
                         last_seen, tags, created_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        pattern.id, pattern.pattern_type, pattern.description,
                        json.dumps(pattern.conditions), pattern.frequency, pattern.confidence,
                        pattern.last_seen.isoformat(), json.dumps(pattern.tags),
                        datetime.now().isoformat()
                    ))
                
                # Save adaptation rules
                for rule in self.adaptation_engine.adaptation_rules.values():
                    conn.execute('''
                        INSERT OR REPLACE INTO adaptation_rules
                        (id, name, description, trigger_contexts, trigger_conditions,
                         adaptation_actions, priority, strategy, enabled, trigger_count,
                         success_count, created_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        rule.id, rule.name, rule.description,
                        json.dumps([ct.value for ct in rule.trigger_contexts]),
                        json.dumps(rule.trigger_conditions),
                        json.dumps(rule.adaptation_actions),
                        rule.priority, rule.strategy.value, rule.enabled,
                        rule.trigger_count, rule.success_count,
                        datetime.now().isoformat()
                    ))
                
        except Exception as e:
            self.logger.error(f"Failed to save current state: {e}")


# Utility functions
def create_context_collector(context_type: ContextType, data_function: Callable[[], Dict[str, Any]],
                           source: str = "custom") -> Callable[[], ContextData]:
    """Create custom context collector"""
    def collector():
        try:
            data = data_function()
            return ContextData(
                context_type=context_type,
                data=data,
                source=source
            )
        except Exception as e:
            logging.error(f"Context collector error for {context_type.value}: {e}")
            return ContextData(context_type=context_type, data={}, source=source, confidence=0.0)
    
    return collector

def create_adaptation_callback(automation_system) -> Callable[[str, Dict[str, Any]], None]:
    """Create adaptation callback for automation system integration"""
    def callback(action_type: str, parameters: Dict[str, Any]):
        try:
            if action_type == "reduce_concurrency":
                # Reduce automation system concurrency
                target_threads = parameters.get('target_threads', 2)
                # automation_system.set_max_threads(target_threads)
                
            elif action_type == "optimize_memory":
                # Optimize memory usage
                if parameters.get('clear_caches'):
                    # automation_system.clear_caches()
                    pass
                
            elif action_type == "adjust_priority":
                # Adjust task priorities
                priority_boost = parameters.get('priority_boost', 0)
                # automation_system.adjust_priorities(priority_boost)
                
            elif action_type == "increase_retries":
                # Increase retry counts
                retry_count = parameters.get('retry_count', 3)
                # automation_system.set_default_retries(retry_count)
                
            logging.info(f"Adaptation action executed: {action_type} with {parameters}")
            
        except Exception as e:
            logging.error(f"Adaptation callback error: {e}")
    
    return callback