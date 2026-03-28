#!/usr/bin/env python3
"""
main.py — Order Service with Event Sourcing pattern for distributed trading system.

exports: create_app() -> FastAPI, OrderService, EventStore
used_by: api_gateway/main.py → route_to_order_service
rules:   Must implement Event Sourcing pattern, store events in SQLite, reconstruct state from events
agent:   deepseek-chat | 2026-03-29 | Created Order Service with Event Sourcing pattern
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import sqlite3

# ============================================================================
# EVENT SOURCING PATTERN
# ============================================================================

class EventType(Enum):
    """Event types for Event Sourcing pattern."""
    ORDER_CREATED = "order_created"
    ORDER_UPDATED = "order_updated"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_COMPLETED = "order_completed"
    ORDER_ITEM_ADDED = "order_item_added"
    ORDER_ITEM_REMOVED = "order_item_removed"

class Event:
    """Event for Event Sourcing pattern."""
    
    def __init__(self, event_type: EventType, aggregate_id: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Initialize event.
        
        Rules:
          - Each event must have unique ID
          - Events are immutable
          - Events contain all data needed to reconstruct state
          - Events are stored in chronological order
        """
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.aggregate_id = aggregate_id
        self.data = data
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.version = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for storage."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "data": json.dumps(self.data),
            "metadata": json.dumps(self.metadata),
            "timestamp": self.timestamp.isoformat(),
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        event = cls(
            event_type=EventType(data["event_type"]),
            aggregate_id=data["aggregate_id"],
            data=json.loads(data["data"]),
            metadata=json.loads(data["metadata"])
        )
        event.event_id = data["event_id"]
        event.timestamp = datetime.fromisoformat(data["timestamp"])
        event.version = data["version"]
        return event

class EventStore:
    """Event Store for Event Sourcing pattern."""
    
    def __init__(self, db_path: str = "order_events.db"):
        """Initialize event store.
        
        Rules:
          - Store events in SQLite database
          - Events must be append-only
          - Support event replay for state reconstruction
          - Support event querying by aggregate ID
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize event store database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                data TEXT NOT NULL,
                metadata TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                version INTEGER NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_aggregate_id ON events (aggregate_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON events (timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def save_event(self, event: Event):
        """Save event to event store."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        event_dict = event.to_dict()
        cursor.execute("""
            INSERT INTO events (event_id, event_type, aggregate_id, data, metadata, timestamp, version)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_dict["event_id"],
            event_dict["event_type"],
            event_dict["aggregate_id"],
            event_dict["data"],
            event_dict["metadata"],
            event_dict["timestamp"],
            event_dict["version"]
        ))
        
        conn.commit()
        conn.close()
    
    def get_events_by_aggregate(self, aggregate_id: str) -> List[Event]:
        """Get all events for an aggregate."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM events 
            WHERE aggregate_id = ? 
            ORDER BY timestamp
        """, (aggregate_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [Event.from_dict(dict(row)) for row in rows]
    
    def get_all_events(self, limit: int = 1000) -> List[Event]:
        """Get all events (for replay)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM events 
            ORDER BY timestamp 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [Event.from_dict(dict(row)) for row in rows]

# ============================================================================
# ORDER AGGREGATE
# ============================================================================

class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class OrderItem:
    """Order item value object."""
    
    def __init__(self, product_id: int, quantity: int, unit_price: float):
        """Initialize order item."""
        self.product_id = product_id
        self.quantity = quantity
        self.unit_price = unit_price
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "product_id": self.product_id,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total": self.quantity * self.unit_price
        }

class OrderAggregate:
    """Order aggregate for Event Sourcing pattern."""
    
    def __init__(self, order_id: Optional[str] = None):
        """Initialize order aggregate.
        
        Rules:
          - State is reconstructed by applying events
          - Events are the source of truth
          - Current state is derived from events
          - Business logic validates commands before creating events
        """
        self.order_id = order_id or str(uuid.uuid4())
        self.user_id: Optional[int] = None
        self.items: List[OrderItem] = []
        self.status = OrderStatus.PENDING
        self.total_amount = 0.0
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None
        self.version = 0
        self._changes: List[Event] = []
    
    def create_order(self, user_id: int, items: List[Dict[str, Any]], correlation_id: str):
        """Create new order command."""
        if self.user_id is not None:
            raise ValueError("Order already created")
        
        # Validate items
        order_items = []
        total_amount = 0.0
        
        for item_data in items:
            product_id = item_data.get("product_id")
            quantity = item_data.get("quantity", 1)
            unit_price = item_data.get("unit_price", 0.0)
            
            if not product_id or quantity <= 0:
                raise ValueError("Invalid item data")
            
            item = OrderItem(product_id, quantity, unit_price)
            order_items.append(item)
            total_amount += item.quantity * item.unit_price
        
        # Create event
        event = Event(
            event_type=EventType.ORDER_CREATED,
            aggregate_id=self.order_id,
            data={
                "user_id": user_id,
                "items": [item.to_dict() for item in order_items],
                "total_amount": total_amount
            },
            metadata={"correlation_id": correlation_id}
        )
        
        # Apply event
        self._apply_event(event)
        self._changes.append(event)
    
    def add_item(self, product_id: int, quantity: int, unit_price: float, correlation_id: str):
        """Add item to order command."""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot add items to non-pending order")
        
        item = OrderItem(product_id, quantity, unit_price)
        
        event = Event(
            event_type=EventType.ORDER_ITEM_ADDED,
            aggregate_id=self.order_id,
            data=item.to_dict(),
            metadata={"correlation_id": correlation_id}
        )
        
        self._apply_event(event)
        self._changes.append(event)
    
    def complete_order(self, correlation_id: str):
        """Complete order command."""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Order cannot be completed")
        
        event = Event(
            event_type=EventType.ORDER_COMPLETED,
            aggregate_id=self.order_id,
            data={},
            metadata={"correlation_id": correlation_id}
        )
        
        self._apply_event(event)
        self._changes.append(event)
    
    def cancel_order(self, reason: str, correlation_id: str):
        """Cancel order command."""
        if self.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
            raise ValueError("Order cannot be cancelled")
        
        event = Event(
            event_type=EventType.ORDER_CANCELLED,
            aggregate_id=self.order_id,
            data={"reason": reason},
            metadata={"correlation_id": correlation_id}
        )
        
        self._apply_event(event)
        self._changes.append(event)
    
    def _apply_event(self, event: Event):
        """Apply event to aggregate state."""
        if event.event_type == EventType.ORDER_CREATED:
            self.user_id = event.data["user_id"]
            self.items = [OrderItem(
                item["product_id"],
                item["quantity"],
                item["unit_price"]
            ) for item in event.data["items"]]
            self.total_amount = event.data["total_amount"]
            self.created_at = event.timestamp
            self.status = OrderStatus.PENDING
        
        elif event.event_type == EventType.ORDER_ITEM_ADDED:
            item = OrderItem(
                event.data["product_id"],
                event.data["quantity"],
                event.data["unit_price"]
            )
            self.items.append(item)
            self.total_amount += item.quantity * item.unit_price
        
        elif event.event_type == EventType.ORDER_COMPLETED:
            self.status = OrderStatus.COMPLETED
        
        elif event.event_type == EventType.ORDER_CANCELLED:
            self.status = OrderStatus.CANCELLED
        
        self.updated_at = event.timestamp
        self.version += 1
    
    def replay_events(self, events: List[Event]):
        """Replay events to reconstruct state."""
        for event in events:
            self._apply_event(event)
    
    def get_changes(self) -> List[Event]:
        """Get pending changes (events to save)."""
        return self._changes.copy()
    
    def clear_changes(self):
        """Clear pending changes."""
        self._changes.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregate to dictionary."""
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "items": [item.to_dict() for item in self.items],
            "status": self.status.value,
            "total_amount": self.total_amount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version
        }

# ============================================================================
# ORDER SERVICE
# ============================================================================

class OrderService:
    """Order Service with Event Sourcing pattern."""
    
    def __init__(self, event_store: EventStore):
        """Initialize order service.
        
        Rules:
          - Use Event Store for persistence
          - Reconstruct aggregates from events
          - Handle commands and produce events
          - Ensure consistency through events
        """
        self.event_store = event_store
    
    def create_order(self, user_id: int, items: List[Dict[str, Any]], correlation_id: str) -> Dict[str, Any]:
        """Create new order."""
        order = OrderAggregate()
        
        try:
            order.create_order(user_id, items, correlation_id)
            
            # Save events
            for event in order.get_changes():
                self.event_store.save_event(event)
            
            order.clear_changes()
            
            return {
                "success": True,
                "order": order.to_dict(),
                "correlation_id": correlation_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "correlation_id": correlation_id
            }
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get order by ID (reconstruct from events)."""
        events = self.event_store.get_events_by_aggregate(order_id)
        
        if not events:
            return {
                "success": False,
                "error": "Order not found"
            }
        
        order = OrderAggregate(order_id)
        order.replay_events(events)
        
        return {
            "success": True,
            "order": order.to_dict()
        }
    
    def complete_order(self, order_id: str, correlation_id: str) -> Dict[str, Any]:
        """Complete order."""
        events = self.event_store.get_events_by_aggregate(order_id)
        
        if not events:
            return {
                "success": False,
                "error": "Order not found"
            }
        
        order = OrderAggregate(order_id)
        order.replay_events(events)
        
        try:
            order.complete_order(correlation_id)
            
            # Save events
            for event in order.get_changes():
                self.event_store.save_event(event)
            
            order.clear_changes()
            
            return {
                "success": True,
                "order": order.to_dict(),
                "correlation_id": correlation_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "correlation_id": correlation_id
            }
    
    def get_all_orders(self, limit: int = 100) -> Dict[str, Any]:
        """Get all orders (for demonstration)."""
        all_events = self.event_store.get_all_events(limit * 10)  # Estimate
        
        # Group events by aggregate
        orders_by_id = {}
        for event in all_events:
            if event.aggregate_id not in orders_by_id:
                orders_by_id[event.aggregate_id] = []
            orders_by_id[event.aggregate_id].append(event)
        
        # Reconstruct orders
        orders = []
        for order_id, events in orders_by_id.items():
            if len(orders) >= limit:
                break
            
            order = OrderAggregate(order_id)
            order.replay_events(events)
            orders.append(order.to_dict())
        
        return {
            "success": True,
            "orders": orders,
            "count": len(orders)
        }

# ============================================================================
# MODELS
# ============================================================================

class OrderCreateRequest(BaseModel):
    """Order creation request model."""
    user_id: int = Field(..., description="User ID")
    items: List[Dict[str, Any]] = Field(..., description="Order items")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")

class OrderCompleteRequest(BaseModel):
    """Order completion request model."""
    correlation_id: Optional[str] = Field(None, description="Correlation ID")

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now)
    event_store_count: int = Field(..., description="Number of events in store")

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    exports: create_app() -> FastAPI
    """
    app = FastAPI(
        title="Order Service",
        description="Order Service with Event Sourcing pattern",
        version="1.0.0"
    )
    
    # Initialize services
    event_store = EventStore("order_events.db")
    order_service = OrderService(event_store)
    
    # Health check endpoint
    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Health check endpoint."""
        # Count events in store
        events = event_store.get_all_events(limit=1)
        count = len(events)  # Simplified count
        
        return HealthResponse(
            status="healthy",
            event_store_count=count
        )
    
    # Create order endpoint
    @app.post("/orders")
    async def create_order(request: OrderCreateRequest):
        """Create a new order."""
        correlation_id = request.correlation_id or str(uuid.uuid4())
        
        result = order_service.create_order(
            user_id=request.user_id,
            items=request.items,
            correlation_id=correlation_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    # Get order endpoint
    @app.get("/orders/{order_id}")
    async def get_order(order_id: str):
        """Get order by ID."""
        result = order_service.get_order(order_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    
    # Complete order endpoint
    @app.post("/orders/{order_id}/complete")
    async def complete_order(order_id: str, request: OrderCompleteRequest):
        """Complete order."""
        correlation_id = request.correlation_id or str(uuid.uuid4())
        
        result = order_service.complete_order(order_id, correlation_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    # Get all orders endpoint (for demonstration)
    @app.get("/orders")
    async def get_all_orders(limit: int = 100):
        """Get all orders."""
        return order_service.get_all_orders(limit)
    
    # Event store endpoint (for demonstration)
    @app.get("/events")
    async def get_events(aggregate_id: Optional[str] = None, limit: int = 100):
        """Get events from event store."""
        if aggregate_id:
            events = event_store.get_events_by_aggregate(aggregate_id)
        else:
            events = event_store.get_all_events(limit)
        
        return {
            "events": [event.to_dict() for event in events],
            "count": len(events)
        }
    
    return app

# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)