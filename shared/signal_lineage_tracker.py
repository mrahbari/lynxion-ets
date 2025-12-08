"""
Signal lineage tracking system for the enterprise hedge fund trading system.
Tracks signal flow from generation to execution with full audit trail.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid
from shared.logger import logger
from shared.metrics import metrics_collector


class SignalEventType(Enum):
    """Types of events in signal lineage"""
    SIGNAL_GENERATED = "signal_generated"
    SIGNAL_RECEIVED = "signal_received" 
    SIGNAL_PROCESSED = "signal_processed"
    SIGNAL_FUSED = "signal_fused"
    SIGNAL_ENHANCED = "signal_enhanced"
    SIGNAL_ROUTED = "signal_routed"
    SIGNAL_VALIDATED = "signal_validated"
    ORDER_CREATED = "order_created"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    EXECUTION_COMPLETED = "execution_completed"
    SIGNAL_DISCARDED = "signal_discarded"


class SignalLineageNode:
    """Represents a node in the signal lineage graph"""
    def __init__(self, 
                 node_id: str,
                 node_type: str,  # 'watcher', 'engine', 'fusion', 'strategy', 'risk', 'broker', etc.
                 component_name: str,
                 event_type: SignalEventType,
                 payload: Dict[str, Any],
                 timestamp: datetime = None):
        self.node_id = node_id
        self.node_type = node_type
        self.component_name = component_name
        self.event_type = event_type
        self.payload = payload
        self.timestamp = timestamp or datetime.now()
        self.parent_nodes: List[str] = []  # IDs of parent nodes
        self.child_nodes: List[str] = []   # IDs of child nodes
        self.tags: Dict[str, str] = {}     # Additional metadata tags


class SignalLineageTracker:
    """Tracks the full lineage of signals through the system"""
    
    def __init__(self):
        self.lineage_graph: Dict[str, SignalLineageNode] = {}  # signal_id -> list of nodes
        self.signal_mapping: Dict[str, List[str]] = {}        # signal_id -> node_ids
        self.component_stats: Dict[str, Dict[str, int]] = {}  # component -> stats
    
    def record_signal_event(self, 
                           signal_id: str,
                           node_type: str,
                           component_name: str, 
                           event_type: SignalEventType,
                           payload: Dict[str, Any],
                           parent_signal_ids: List[str] = None,
                           tags: Dict[str, str] = None) -> str:
        """Record a signal event in the lineage"""
        node_id = str(uuid.uuid4())
        
        node = SignalLineageNode(
            node_id=node_id,
            node_type=node_type,
            component_name=component_name,
            event_type=event_type,
            payload=payload,
            timestamp=datetime.now()
        )
        
        node.tags = tags or {}
        
        # Link to parent nodes if provided
        if parent_signal_ids:
            for parent_id in parent_signal_ids:
                if parent_id in self.lineage_graph:
                    self.lineage_graph[parent_id].child_nodes.append(node_id)
                    node.parent_nodes.append(parent_id)
        
        # Store the node
        if signal_id not in self.lineage_graph:
            self.lineage_graph[signal_id] = {}
        
        self.lineage_graph[signal_id][node_id] = node
        
        # Update signal mapping
        if signal_id not in self.signal_mapping:
            self.signal_mapping[signal_id] = []
        self.signal_mapping[signal_id].append(node_id)
        
        # Update component stats
        if component_name not in self.component_stats:
            self.component_stats[component_name] = {
                'events_processed': 0,
                'avg_processing_time': 0,
                'last_event_time': datetime.now()
            }
        self.component_stats[component_name]['events_processed'] += 1
        self.component_stats[component_name]['last_event_time'] = datetime.now()
        
        # Record metrics
        metrics_collector.record_performance_metric(
            f"signal_lineage_{event_type.value}",
            0.0001,  # Placeholder - actual processing time would be calculated
            {'component': component_name, 'event_type': event_type.value}
        )
        
        logger.info(f"Signal lineage recorded: {event_type.value}", 
                   signal_id=signal_id, 
                   component=component_name,
                   event_type=event_type.value,
                   node_id=node_id)
        
        return node_id
    
    def get_signal_lineage(self, signal_id: str) -> List[SignalLineageNode]:
        """Get the full lineage for a signal"""
        if signal_id not in self.signal_mapping:
            return []
        
        node_ids = self.signal_mapping[signal_id]
        nodes = [self.lineage_graph[signal_id][node_id] for node_id in node_ids]
        
        # Sort by timestamp to show chronological order
        return sorted(nodes, key=lambda x: x.timestamp)
    
    def get_signal_path(self, signal_id: str) -> str:
        """Get a human-readable path of the signal through the system"""
        lineage = self.get_signal_lineage(signal_id)
        if not lineage:
            return f"Signal {signal_id}: No lineage recorded"
        
        path = [f"Signal {signal_id} path:"]
        for node in lineage:
            path.append(f"  -> {node.timestamp.strftime('%H:%M:%S.%f')[:-3]} | {node.component_name} | {node.event_type.value}")
        
        return "\\n".join(path)
    
    def get_component_analysis(self, component_name: str) -> Dict[str, Any]:
        """Get analysis for a specific component"""
        if component_name not in self.component_stats:
            return {}
        
        stats = self.component_stats[component_name]
        
        # Count events by type for this component
        event_counts = {}
        for signal_id, nodes in self.lineage_graph.items():
            for node in nodes.values():
                if node.component_name == component_name:
                    event_type = node.event_type.value
                    event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return {
            'component': component_name,
            'events_processed': stats['events_processed'],
            'last_event_time': stats['last_event_time'],
            'event_counts_by_type': event_counts
        }
    
    def find_bottlenecks(self) -> List[Dict[str, Any]]:
        """Find potential bottlenecks in signal processing"""
        bottlenecks = []
        
        # Look for components with high event counts or processing delays
        for component_name, stats in self.component_stats.items():
            if stats['events_processed'] > 100:  # Arbitrary threshold
                bottlenecks.append({
                    'component': component_name,
                    'events_processed': stats['events_processed'],
                    'last_event_time': stats['last_event_time'],
                    'potential_bottleneck': True
                })
        
        return bottlenecks
    
    def get_signals_by_status(self, status: SignalEventType) -> List[str]:
        """Get all signals that had a specific event type"""
        matching_signals = []
        
        for signal_id, nodes in self.lineage_graph.items():
            for node in nodes.values():
                if node.event_type == status:
                    if signal_id not in matching_signals:
                        matching_signals.append(signal_id)
        
        return matching_signals
    
    def get_full_audit_trail(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get full audit trail for all signals"""
        audit_trail = {}
        
        for signal_id in self.signal_mapping.keys():
            lineage = self.get_signal_lineage(signal_id)
            audit_trail[signal_id] = [
                {
                    'node_id': node.node_id,
                    'component': node.component_name,
                    'event_type': node.event_type.value,
                    'timestamp': node.timestamp.isoformat(),
                    'payload_keys': list(node.payload.keys()),
                    'tags': node.tags
                }
                for node in lineage
            ]
        
        return audit_trail


class SignalTracker:
    """Simplified interface for tracking individual signals through the system"""
    
    def __init__(self, lineage_tracker: SignalLineageTracker):
        self.lineage_tracker = lineage_tracker
    
    def signal_generated(self, signal_id: str, component: str, signal_data: Dict[str, Any], tags: Dict[str, str] = None):
        """Track when a signal is generated"""
        self.lineage_tracker.record_signal_event(
            signal_id=signal_id,
            node_type='watcher',
            component_name=component,
            event_type=SignalEventType.SIGNAL_GENERATED,
            payload=signal_data,
            tags=tags
        )
    
    def signal_processed(self, signal_id: str, component: str, original_signal_id: str = None, processed_data: Dict[str, Any] = None, tags: Dict[str, str] = None):
        """Track when a signal is processed by an engine or other component"""
        parent_ids = [original_signal_id] if original_signal_id else []
        self.lineage_tracker.record_signal_event(
            signal_id=signal_id,
            node_type='engine',
            component_name=component,
            event_type=SignalEventType.SIGNAL_PROCESSED,
            payload=processed_data or {},
            parent_signal_ids=parent_ids,
            tags=tags
        )
    
    def signal_fused(self, fused_signal_id: str, component: str, original_signal_ids: List[str], fused_data: Dict[str, Any] = None, tags: Dict[str, str] = None):
        """Track when signals are fused"""
        self.lineage_tracker.record_signal_event(
            signal_id=fused_signal_id,
            node_type='fusion',
            component_name=component,
            event_type=SignalEventType.SIGNAL_FUSED,
            payload=fused_data or {},
            parent_signal_ids=original_signal_ids,
            tags=tags
        )
    
    def signal_validated(self, signal_id: str, component: str, validation_result: Dict[str, Any], tags: Dict[str, str] = None):
        """Track when a signal passes risk validation"""
        self.lineage_tracker.record_signal_event(
            signal_id=signal_id,
            node_type='risk',
            component_name=component,
            event_type=SignalEventType.SIGNAL_VALIDATED,
            payload=validation_result,
            tags=tags
        )
    
    def order_created(self, signal_id: str, component: str, order_data: Dict[str, Any], tags: Dict[str, str] = None):
        """Track when an order is created from a signal"""
        self.lineage_tracker.record_signal_event(
            signal_id=signal_id,
            node_type='broker',
            component_name=component,
            event_type=SignalEventType.ORDER_CREATED,
            payload=order_data,
            tags=tags
        )
    
    def order_filled(self, signal_id: str, component: str, fill_data: Dict[str, Any], tags: Dict[str, str] = None):
        """Track when an order is filled"""
        self.lineage_tracker.record_signal_event(
            signal_id=signal_id,
            node_type='broker', 
            component_name=component,
            event_type=SignalEventType.ORDER_FILLED,
            payload=fill_data,
            tags=tags
        )


# Global signal lineage tracker instance
signal_lineage_tracker = SignalLineageTracker()
signal_tracker = SignalTracker(signal_lineage_tracker)