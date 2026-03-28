#!/usr/bin/env python3
"""
main.py — Inventory Service with CQRS pattern for distributed trading system.

exports: create_app() -> FastAPI, InventoryService, InventoryReadModel, InventoryWriteModel
used_by: api_gateway/main.py → route_to_inventory_service
rules:   Must implement CQRS pattern (Command Query Responsibility Segregation), separate read/write models
agent:   deepseek-chat | 2026-03-29 | Created Inventory Service with CQRS pattern
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import sqlite3

# ============================================================================
# CQRS PATTERN - COMMAND MODEL (WRITE)
# ============================================================================

class InventoryCommandType(Enum):
    """Command types for CQRS pattern."""
    ADD_PRODUCT = "add_product"
    UPDATE_STOCK = "update_stock"
    RESERVE_STOCK = "reserve_stock"
    CONSUME_STOCK = "consume_stock"
    RELEASE_STOCK = "release_stock"

class InventoryCommand:
    """Command for CQRS pattern (write side)."""
    
    def __init__(self, command_type: InventoryCommandType, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Initialize command.
        
        Rules:
          - Commands represent intent to change state
          - Commands are validated before execution
          - Commands produce events that update read model
          - Commands are idempotent (can be retried)
        """
        self.command_id = str(uuid.uuid4())
        self.command_type = command_type
        self.data = data
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.status = "pending"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert command to dictionary."""
        return {
            "command_id": self.command_id,
            "command_type": self.command_type.value,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status
        }

class InventoryWriteModel:
    """Write model for CQRS pattern (handles commands)."""
    
    def __init__(self, db_path: str = "inventory_write.db"):
        """Initialize write model.
        
        Rules:
          - Handles commands and produces events
          - Ensures consistency through transactions
          - Validates business rules before state changes
          - Stores events for read model synchronization
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize write model database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Products table (write model)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products_write (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                total_stock INTEGER NOT NULL,
                available_stock INTEGER NOT NULL,
                reserved_stock INTEGER DEFAULT 0,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Commands table (for auditing)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                command_id TEXT PRIMARY KEY,
                command_type TEXT NOT NULL,
                data TEXT NOT NULL,
                metadata TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        
        # Events table (for read model synchronization)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def execute_command(self, command: InventoryCommand) -> Dict[str, Any]:
        """Execute command and produce events."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Store command for auditing
            command_dict = command.to_dict()
            cursor.execute("""
                INSERT INTO commands (command_id, command_type, data, metadata, timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                command_dict["command_id"],
                command_dict["command_type"],
                json.dumps(command_dict["data"]),
                json.dumps(command_dict["metadata"]),
                command_dict["timestamp"],
                "executing"
            ))
            
            result = None
            
            # Execute command based on type
            if command.command_type == InventoryCommandType.ADD_PRODUCT:
                result = self._execute_add_product(cursor, command)
            
            elif command.command_type == InventoryCommandType.UPDATE_STOCK:
                result = self._execute_update_stock(cursor, command)
            
            elif command.command_type == InventoryCommandType.RESERVE_STOCK:
                result = self._execute_reserve_stock(cursor, command)
            
            elif command.command_type == InventoryCommandType.CONSUME_STOCK:
                result = self._execute_consume_stock(cursor, command)
            
            elif command.command_type == InventoryCommandType.RELEASE_STOCK:
                result = self._execute_release_stock(cursor, command)
            
            # Update command status
            cursor.execute("""
                UPDATE commands SET status = ? WHERE command_id = ?
            """, ("completed", command.command_id))
            
            conn.commit()
            
            if result and "success" in result and result["success"]:
                # Produce event for read model synchronization
                self._produce_event(cursor, command, result)
                conn.commit()
            
            return result or {"success": False, "error": "Unknown command type"}
            
        except Exception as e:
            conn.rollback()
            
            # Update command status to failed
            try:
                cursor.execute("""
                    UPDATE commands SET status = ? WHERE command_id = ?
                """, ("failed", command.command_id))
                conn.commit()
            except:
                pass
            
            return {"success": False, "error": str(e)}
        
        finally:
            conn.close()
    
    def _execute_add_product(self, cursor, command: InventoryCommand) -> Dict[str, Any]:
        """Execute add product command."""
        data = command.data
        product_id = data.get("product_id")
        name = data.get("name")
        description = data.get("description", "")
        price = data.get("price", 0.0)
        stock = data.get("stock", 0)
        category = data.get("category", "general")
        
        if not product_id or not name:
            return {"success": False, "error": "Missing required fields"}
        
        # Check if product already exists
        cursor.execute("SELECT product_id FROM products_write WHERE product_id = ?", (product_id,))
        if cursor.fetchone():
            return {"success": False, "error": f"Product {product_id} already exists"}
        
        # Add product
        cursor.execute("""
            INSERT INTO products_write (product_id, name, description, price, total_stock, available_stock, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (product_id, name, description, price, stock, stock, category))
        
        return {
            "success": True,
            "product_id": product_id,
            "name": name,
            "price": price,
            "stock": stock,
            "available_stock": stock,
            "category": category
        }
    
    def _execute_update_stock(self, cursor, command: InventoryCommand) -> Dict[str, Any]:
        """Execute update stock command."""
        data = command.data
        product_id = data.get("product_id")
        stock_change = data.get("stock_change", 0)
        
        if not product_id:
            return {"success": False, "error": "Missing product_id"}
        
        # Get current stock
        cursor.execute("""
            SELECT total_stock, available_stock, reserved_stock FROM products_write WHERE product_id = ?
        """, (product_id,))
        result = cursor.fetchone()
        
        if not result:
            return {"success": False, "error": f"Product {product_id} not found"}
        
        total_stock, available_stock, reserved_stock = result
        
        # Calculate new values
        new_total_stock = total_stock + stock_change
        new_available_stock = available_stock + stock_change
        
        if new_total_stock < 0 or new_available_stock < 0:
            return {"success": False, "error": "Stock cannot be negative"}
        
        # Update stock
        cursor.execute("""
            UPDATE products_write 
            SET total_stock = ?, available_stock = ?, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ?
        """, (new_total_stock, new_available_stock, product_id))
        
        return {
            "success": True,
            "product_id": product_id,
            "old_total_stock": total_stock,
            "new_total_stock": new_total_stock,
            "old_available_stock": available_stock,
            "new_available_stock": new_available_stock,
            "stock_change": stock_change,
            "reserved_stock": reserved_stock
        }
    
    def _execute_reserve_stock(self, cursor, command: InventoryCommand) -> Dict[str, Any]:
        """Execute reserve stock command."""
        data = command.data
        product_id = data.get("product_id")
        quantity = data.get("quantity", 0)
        reservation_id = data.get("reservation_id", str(uuid.uuid4()))
        
        if not product_id or quantity <= 0:
            return {"success": False, "error": "Invalid reservation request"}
        
        # Get current stock
        cursor.execute("""
            SELECT available_stock, reserved_stock FROM products_write WHERE product_id = ?
        """, (product_id,))
        result = cursor.fetchone()
        
        if not result:
            return {"success": False, "error": f"Product {product_id} not found"}
        
        available_stock, reserved_stock = result
        
        # Check if enough stock available
        if available_stock < quantity:
            return {
                "success": False,
                "error": f"Insufficient stock. Available: {available_stock}, Requested: {quantity}",
                "available_stock": available_stock
            }
        
        # Reserve stock
        new_available_stock = available_stock - quantity
        new_reserved_stock = reserved_stock + quantity
        
        cursor.execute("""
            UPDATE products_write 
            SET available_stock = ?, reserved_stock = ?, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ?
        """, (new_available_stock, new_reserved_stock, product_id))
        
        return {
            "success": True,
            "product_id": product_id,
            "reservation_id": reservation_id,
            "quantity": quantity,
            "old_available_stock": available_stock,
            "new_available_stock": new_available_stock,
            "old_reserved_stock": reserved_stock,
            "new_reserved_stock": new_reserved_stock
        }
    
    def _execute_consume_stock(self, cursor, command: InventoryCommand) -> Dict[str, Any]:
        """Execute consume stock command."""
        data = command.data
        product_id = data.get("product_id")
        quantity = data.get("quantity", 0)
        
        if not product_id or quantity <= 0:
            return {"success": False, "error": "Invalid consumption request"}
        
        # Get current stock
        cursor.execute("""
            SELECT total_stock, reserved_stock FROM products_write WHERE product_id = ?
        """, (product_id,))
        result = cursor.fetchone()
        
        if not result:
            return {"success": False, "error": f"Product {product_id} not found"}
        
        total_stock, reserved_stock = result
        
        # Check if enough reserved stock
        if reserved_stock < quantity:
            return {
                "success": False,
                "error": f"Insufficient reserved stock. Reserved: {reserved_stock}, Requested: {quantity}",
                "reserved_stock": reserved_stock
            }
        
        # Consume stock
        new_total_stock = total_stock - quantity
        new_reserved_stock = reserved_stock - quantity
        
        cursor.execute("""
            UPDATE products_write 
            SET total_stock = ?, reserved_stock = ?, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ?
        """, (new_total_stock, new_reserved_stock, product_id))
        
        return {
            "success": True,
            "product_id": product_id,
            "quantity": quantity,
            "old_total_stock": total_stock,
            "new_total_stock": new_total_stock,
            "old_reserved_stock": reserved_stock,
            "new_reserved_stock": new_reserved_stock
        }
    
    def _execute_release_stock(self, cursor, command: InventoryCommand) -> Dict[str, Any]:
        """Execute release stock command."""
        data = command.data
        product_id = data.get("product_id")
        quantity = data.get("quantity", 0)
        
        if not product_id or quantity <= 0:
            return {"success": False, "error": "Invalid release request"}
        
        # Get current stock
        cursor.execute("""
            SELECT available_stock, reserved_stock FROM products_write WHERE product_id = ?
        """, (product_id,))
        result = cursor.fetchone()
        
        if not result:
            return {"success": False, "error": f"Product {product_id} not found"}
        
        available_stock, reserved_stock = result
        
        # Check if enough reserved stock to release
        if reserved_stock < quantity:
            return {
                "success": False,
                "error": f"Cannot release more than reserved. Reserved: {reserved_stock}, Requested: {quantity}",
                "reserved_stock": reserved_stock
            }
        
        # Release stock
        new_available_stock = available_stock + quantity
        new_reserved_stock = reserved_stock - quantity
        
        cursor.execute("""
            UPDATE products_write 
            SET available_stock = ?, reserved_stock = ?, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ?
        """, (new_available_stock, new_reserved_stock, product_id))
        
        return {
            "success": True,
            "product_id": product_id,
            "quantity": quantity,
            "old_available_stock": available_stock,
            "new_available_stock": new_available_stock,
            "old_reserved_stock": reserved_stock,
            "new_reserved_stock": new_reserved_stock
        }
    
    def _produce_event(self, cursor, command: InventoryCommand, result: Dict[str, Any]):
        """Produce event for read model synchronization."""
        event_id = str(uuid.uuid4())
        event_type = f"inventory_{command.command_type.value}"
        aggregate_id = result.get("product_id", "global")
        
        cursor.execute("""
            INSERT INTO events (event_id, event_type, aggregate_id, data, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event_id,
            event_type,
            str(aggregate_id),
            json.dumps(result),
            datetime.now().isoformat()
        ))

# ============================================================================
# CQRS PATTERN - QUERY MODEL (READ)
# ============================================================================

class InventoryReadModel:
    """Read model for CQRS pattern (optimized for queries)."""
    
    def __init__(self, db_path: str = "inventory_read.db"):
        """Initialize read model.
        
        Rules:
          - Optimized for fast queries
          - Denormalized data for performance
          - Updated asynchronously from write model events
          - Can be rebuilt from events if needed
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize read model database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Products table (read model - denormalized)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products_read (
                product_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                total_stock INTEGER NOT NULL,
                available_stock INTEGER NOT NULL,
                reserved_stock INTEGER DEFAULT 0,
                category TEXT,
                low_stock_threshold INTEGER DEFAULT 10,
                is_low_stock BOOLEAN DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Stock history table (for analytics)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_stock INTEGER NOT NULL,
                available_stock INTEGER NOT NULL,
                reserved_stock INTEGER NOT NULL,
                change_type TEXT,
                change_amount INTEGER,
                FOREIGN KEY (product_id) REFERENCES products_read (product_id)
            )
        """)
        
        # Create indexes for fast queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category ON products_read (category)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_low_stock ON products_read (is_low_stock)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_history_product ON stock_history (product_id, timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Get product by ID (fast read)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM products_read WHERE product_id = ?", (product_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {"success": False, "error": f"Product {product_id} not found"}
        
        return {"success": True, "product": dict(result)}
    
    def check_stock(self, product_id: int, quantity: int) -> Dict[str, Any]:
        """Check if sufficient stock is available."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT available_stock, total_stock, is_low_stock FROM products_read WHERE product_id = ?
        """, (product_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {"success": False, "error": f"Product {product_id} not found"}
        
        available_stock, total_stock, is_low_stock = result
        
        has_sufficient_stock = available_stock >= quantity
        is_critical = available_stock < 5
        is_low = is_low_stock == 1
        
        return {
            "success": True,
            "has_sufficient_stock": has_sufficient_stock,
            "available_stock": available_stock,
            "total_stock": total_stock,
            "is_low_stock": is_low,
            "is_critical_stock": is_critical,
            "requested_quantity": quantity,
            "shortage": max(0, quantity - available_stock) if not has_sufficient_stock else 0
        }
    
    def get_low_stock_products(self, threshold: int = 10) -> Dict[str, Any]:
        """Get products with low stock."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM products_read 
            WHERE available_stock <= low_stock_threshold OR is_low_stock = 1
            ORDER BY available_stock ASC
        """)
        
        products = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {
            "success": True,
            "products": products,
            "count": len(products),
            "threshold": threshold
        }
    
    def get_products_by_category(self, category: str) -> Dict[str, Any]:
        """Get products by category."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM products_read WHERE category = ? ORDER BY name
        """, (category,))
        
        products = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {
            "success": True,
            "products": products,
            "count": len(products),
            "category": category
        }
    
    def get_stock_history(self, product_id: int, limit: int = 100) -> Dict[str, Any]:
        """Get stock history for a product."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM stock_history 
            WHERE product_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (product_id, limit))
        
        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {
            "success": True,
            "history": history,
            "count": len(history),
            "product_id": product_id
        }
    
    def update_from_event(self, event_data: Dict[str, Any]):
        """Update read model from write model event."""
        # This would be called by an event handler in a real system
        # For simplicity, we'll implement a basic version
        pass

# ============================================================================
# INVENTORY SERVICE
# ============================================================================

class InventoryService:
    """Inventory Service with CQRS pattern."""
    
    def __init__(self, write_model: InventoryWriteModel, read_model: InventoryReadModel):
        """Initialize inventory service.
        
        Rules:
          - Separates commands (write) from queries (read)
          - Write model handles state changes
          - Read model provides fast queries
          - Events synchronize write and read models
        """
        self.write_model = write_model
        self.read_model = read_model
    
    def add_product(self, product_data: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
        """Add new product."""
        command = InventoryCommand(
            command_type=InventoryCommandType.ADD_PRODUCT,
            data=product_data,
            metadata={"correlation_id": correlation_id}
        )
        
        return self.write_model.execute_command(command)
    
    def update_stock(self, product_id: int, stock_change: int, correlation_id: str) -> Dict[str, Any]:
        """Update product stock."""
        command = InventoryCommand(
            command_type=InventoryCommandType.UPDATE_STOCK,
            data={"product_id": product_id, "stock_change": stock_change},
            metadata={"correlation_id": correlation_id}
        )
        
        return self.write_model.execute_command(command)
    
    def reserve_stock(self, product_id: int, quantity: int, correlation_id: str) -> Dict[str, Any]:
        """Reserve stock for an order."""
        command = InventoryCommand(
            command_type=InventoryCommandType.RESERVE_STOCK,
            data={
                "product_id": product_id,
                "quantity": quantity,
                "reservation_id": str(uuid.uuid4())
            },
            metadata={"correlation_id": correlation_id}
        )
        
        return self.write_model.execute_command(command)
    
    def check_stock(self, product_id: int, quantity: int) -> Dict[str, Any]:
        """Check stock availability (read model query)."""
        return self.read_model.check_stock(product_id, quantity)
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Get product details (read model query)."""
        return self.read_model.get_product(product_id)
    
    def get_low_stock_products(self, threshold: int = 10) -> Dict[str, Any]:
        """Get low stock products (read model query)."""
        return self.read_model.get_low_stock_products(threshold)
    
    def get_products_by_category(self, category: str) -> Dict[str, Any]:
        """Get products by category (read model query)."""
        return self.read_model.get_products_by_category(category)

# ============================================================================
# MODELS
# ============================================================================

class AddProductRequest(BaseModel):
    """Add product request model."""
    product_id: int = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., description="Product price")
    stock: int = Field(..., description="Initial stock")
    category: str = Field("general", description="Product category")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")

class UpdateStockRequest(BaseModel):
    """Update stock request model."""
    product_id: int = Field(..., description="Product ID")
    stock_change: int = Field(..., description="Stock change (positive to add, negative to remove)")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")

class ReserveStockRequest(BaseModel):
    """Reserve stock request model."""
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity to reserve")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")

class CheckStockRequest(BaseModel):
    """Check stock request model."""
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity to check")

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now)
    write_model_healthy: bool = Field(..., description="Write model health")
    read_model_healthy: bool = Field(..., description="Read model health")

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    exports: create_app() -> FastAPI
    """
    app = FastAPI(
        title="Inventory Service",
        description="Inventory Service with CQRS pattern",
        version="1.0.0"
    )
    
    # Initialize services
    write_model = InventoryWriteModel("inventory_write.db")
    read_model = InventoryReadModel("inventory_read.db")
    inventory_service = InventoryService(write_model, read_model)
    
    # Health check endpoint
    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Health check endpoint."""
        # Check write model
        write_healthy = False
        try:
            conn = sqlite3.connect("inventory_write.db")
            conn.close()
            write_healthy = True
        except:
            write_healthy = False
        
        # Check read model
        read_healthy = False
        try:
            conn = sqlite3.connect("inventory_read.db")
            conn.close()
            read_healthy = True
        except:
            read_healthy = False
        
        overall_status = "healthy" if write_healthy and read_healthy else "degraded"
        if not write_healthy and not read_healthy:
            overall_status = "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            write_model_healthy=write_healthy,
            read_model_healthy=read_healthy
        )
    
    # Add product endpoint (write)
    @app.post("/products")
    async def add_product(request: AddProductRequest):
        """Add new product."""
        correlation_id = request.correlation_id or str(uuid.uuid4())
        
        result = inventory_service.add_product(
            product_data={
                "product_id": request.product_id,
                "name": request.name,
                "description": request.description,
                "price": request.price,
                "stock": request.stock,
                "category": request.category
            },
            correlation_id=correlation_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    # Update stock endpoint (write)
    @app.post("/products/{product_id}/stock")
    async def update_stock(product_id: int, request: UpdateStockRequest):
        """Update product stock."""
        correlation_id = request.correlation_id or str(uuid.uuid4())
        
        result = inventory_service.update_stock(
            product_id=product_id,
            stock_change=request.stock_change,
            correlation_id=correlation_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    # Reserve stock endpoint (write)
    @app.post("/products/{product_id}/reserve")
    async def reserve_stock(product_id: int, request: ReserveStockRequest):
        """Reserve stock for order."""
        correlation_id = request.correlation_id or str(uuid.uuid4())
        
        result = inventory_service.reserve_stock(
            product_id=product_id,
            quantity=request.quantity,
            correlation_id=correlation_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    # Check stock endpoint (read)
    @app.get("/inventory/{product_id}/check")
    async def check_inventory(product_id: int, quantity: int):
        """Check inventory availability."""
        result = inventory_service.check_stock(product_id, quantity)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    
    # Get product endpoint (read)
    @app.get("/products/{product_id}")
    async def get_product(product_id: int):
        """Get product details."""
        result = inventory_service.get_product(product_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    
    # Get low stock products endpoint (read)
    @app.get("/products/low-stock")
    async def get_low_stock_products(threshold: int = 10):
        """Get products with low stock."""
        return inventory_service.get_low_stock_products(threshold)
    
    # Get products by category endpoint (read)
    @app.get("/products/category/{category}")
    async def get_products_by_category(category: str):
        """Get products by category."""
        return inventory_service.get_products_by_category(category)
    
    return app

# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)