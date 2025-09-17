"""
Event Registry - Central registration for all domain event handlers
"""
from typing import Dict, List, Callable
from app.core.infrastructure.event_bus import event_bus

class EventRegistry:
    """Central registry for domain event handlers"""
    
    def __init__(self):
        self.registered_handlers: Dict[str, List[str]] = {}
    
    def register_handler(self, event_type: str, handler: Callable, domain: str = "core"):
        """Register a handler for an event type"""
        try:
            event_bus.subscribe(event_type, handler)
            
            # Track registration for monitoring
            if event_type not in self.registered_handlers:
                self.registered_handlers[event_type] = []
            
            handler_info = f"{domain}.{handler.__name__}"
            self.registered_handlers[event_type].append(handler_info)
            
            print(f"✅ Registered {handler_info} for event: {event_type}")
            
        except Exception as e:
            print(f"❌ Failed to register handler {handler.__name__}: {e}")
    
    def register_domain_handlers(self):
        """Register all domain handlers"""
        print("🔧 Registering domain event handlers...")
        
        try:
            # QR Generation Domain Handlers
            from app.domains.qr_generation.handlers import qr_event_handler
            self.register_handler(
                "approval.instance.updated", 
                qr_event_handler.handle_approval_event,
                "qr_generation"
            )
            
            # Validation Domain Handlers  
            from app.domains.validation.handlers import validation_event_handler
            self.register_handler(
                "approval.instance.updated",
                validation_event_handler.handle_approval_event, 
                "validation"
            )
            
            print(f"✅ Successfully registered handlers for {len(self.registered_handlers)} event types")
            
        except Exception as e:
            print(f"❌ Error registering domain handlers: {e}")
            raise
    
    def get_registration_status(self) -> Dict:
        """Get current registration status"""
        total_handlers = sum(len(handlers) for handlers in self.registered_handlers.values())
        
        return {
            "total_event_types": len(self.registered_handlers),
            "total_handlers": total_handlers,
            "registrations": self.registered_handlers,
            "event_bus_handlers": len(event_bus.handlers)
        }

# Global registry instance
event_registry = EventRegistry()
