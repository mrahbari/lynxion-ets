from typing import Callable, Dict, List, Any
import threading
import queue
import time

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_queue = queue.Queue()
        self.running = True
        
    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to an event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        
    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from an event type"""
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(callback)
            except ValueError:
                pass  # Callback was not subscribed
                
    def publish(self, event_type: str, data: Any):
        """Publish an event to the bus"""
        self.event_queue.put((event_type, data))
        
    def _process_events(self):
        """Internal method to process events in a separate thread"""
        while self.running:
            try:
                event_type, data = self.event_queue.get(timeout=0.1)
                
                # Notify all subscribers of this event type
                if event_type in self.subscribers:
                    for callback in self.subscribers[event_type]:
                        try:
                            callback(data)
                        except Exception as e:
                            print(f"Error in event callback: {e}")
                            
            except queue.Empty:
                continue
                
    def start(self):
        """Start the event processing thread"""
        self.thread = threading.Thread(target=self._process_events, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Stop the event bus"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)

# Global event bus instance
event_bus = EventBus()