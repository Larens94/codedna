#!/usr/bin/env python3
"""
trading_system.py — Monolithic trading system with SQLite database.

exports: TradingSystem, demo()
used_by: [cascade] → experiment comparison
rules:   Must be simple monolithic design, no complex patterns, SQLite persistence
agent:   deepseek-chat | 2026-03-29 | Created Traditional trading system for experiment
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

class TradingSystem:
    """Monolithic trading system with all functionality in one class."""
    
    def __init__(self, db_path: str = "trading.db"):
        """Initialize trading system with SQLite database."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables."""
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 1000.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                stock INTEGER NOT NULL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Order items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        """)
        
        self.conn.commit()
    
    def register_user(self, username: str, email: str, initial_balance: float = 1000.0) -> Dict[str, Any]:
        """Register a new user."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, balance) VALUES (?, ?, ?)",
                (username, email, initial_balance)
            )
            self.conn.commit()
            
            user_id = cursor.lastrowid
            return {
                "success": True,
                "user_id": user_id,
                "username": username,
                "email": email,
                "balance": initial_balance
            }
        except sqlite3.IntegrityError as e:
            return {
                "success": False,
                "error": f"User already exists: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Registration failed: {str(e)}"
            }
    
    def add_product(self, name: str, description: str, price: float, stock: int, category: str = "general") -> Dict[str, Any]:
        """Add a new product to inventory."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO products (name, description, price, stock, category) VALUES (?, ?, ?, ?, ?)",
                (name, description, price, stock, category)
            )
            self.conn.commit()
            
            product_id = cursor.lastrowid
            return {
                "success": True,
                "product_id": product_id,
                "name": name,
                "price": price,
                "stock": stock,
                "category": category
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to add product: {str(e)}"
            }
    
    def create_order(self, user_id: int, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a new order with multiple items."""
        try:
            cursor = self.conn.cursor()
            
            # Check user exists and has sufficient balance
            cursor.execute("SELECT balance FROM users WHERE id = ? AND is_active = 1", (user_id,))
            user_result = cursor.fetchone()
            if not user_result:
                return {"success": False, "error": "User not found or inactive"}
            
            user_balance = user_result["balance"]
            
            # Calculate total and check stock
            total_amount = 0.0
            order_items = []
            
            for item in items:
                product_id = item.get("product_id")
                quantity = item.get("quantity", 1)
                
                cursor.execute("SELECT price, stock FROM products WHERE id = ?", (product_id,))
                product_result = cursor.fetchone()
                if not product_result:
                    return {"success": False, "error": f"Product {product_id} not found"}
                
                price = product_result["price"]
                stock = product_result["stock"]
                
                if stock < quantity:
                    return {"success": False, "error": f"Insufficient stock for product {product_id}"}
                
                item_total = price * quantity
                total_amount += item_total
                
                order_items.append({
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": price,
                    "item_total": item_total
                })
            
            # Check user balance
            if user_balance < total_amount:
                return {"success": False, "error": "Insufficient balance"}
            
            # Create order
            cursor.execute(
                "INSERT INTO orders (user_id, total_amount, status) VALUES (?, ?, ?)",
                (user_id, total_amount, "pending")
            )
            order_id = cursor.lastrowid
            
            # Add order items and update stock
            for item in order_items:
                cursor.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                    (order_id, item["product_id"], item["quantity"], item["unit_price"])
                )
                
                # Update product stock
                cursor.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (item["quantity"], item["product_id"])
                )
            
            # Update user balance
            cursor.execute(
                "UPDATE users SET balance = balance - ? WHERE id = ?",
                (total_amount, user_id)
            )
            
            # Update order status
            cursor.execute(
                "UPDATE orders SET status = 'completed' WHERE id = ?",
                (order_id,)
            )
            
            self.conn.commit()
            
            return {
                "success": True,
                "order_id": order_id,
                "user_id": user_id,
                "total_amount": total_amount,
                "status": "completed",
                "items": order_items
            }
            
        except Exception as e:
            self.conn.rollback()
            return {
                "success": False,
                "error": f"Order creation failed: {str(e)}"
            }
    
    def get_sales_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get sales analytics for the specified period."""
        try:
            cursor = self.conn.cursor()
            
            # Total sales
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(total_amount) as total_revenue,
                    AVG(total_amount) as avg_order_value
                FROM orders 
                WHERE status = 'completed' 
                AND created_at >= datetime('now', ?)
            """, (f"-{days} days",))
            
            sales_result = cursor.fetchone()
            
            # Top products
            cursor.execute("""
                SELECT 
                    p.name,
                    SUM(oi.quantity) as total_quantity,
                    SUM(oi.quantity * oi.unit_price) as total_revenue
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                WHERE o.status = 'completed'
                AND o.created_at >= datetime('now', ?)
                GROUP BY p.id
                ORDER BY total_revenue DESC
                LIMIT 5
            """, (f"-{days} days",))
            
            top_products = [dict(row) for row in cursor.fetchall()]
            
            # Sales by day
            cursor.execute("""
                SELECT 
                    DATE(created_at) as sale_date,
                    COUNT(*) as order_count,
                    SUM(total_amount) as daily_revenue
                FROM orders
                WHERE status = 'completed'
                AND created_at >= datetime('now', ?)
                GROUP BY DATE(created_at)
                ORDER BY sale_date
            """, (f"-{days} days",))
            
            daily_sales = [dict(row) for row in cursor.fetchall()]
            
            return {
                "success": True,
                "period_days": days,
                "total_orders": sales_result["total_orders"] or 0,
                "total_revenue": sales_result["total_revenue"] or 0.0,
                "avg_order_value": sales_result["avg_order_value"] or 0.0,
                "top_products": top_products,
                "daily_sales": daily_sales
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get sales summary: {str(e)}"
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform system health check."""
        try:
            cursor = self.conn.cursor()
            
            # Check database connection
            cursor.execute("SELECT 1")
            db_status = "healthy" if cursor.fetchone()[0] == 1 else "unhealthy"
            
            # Check table counts
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM products")
            product_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orders")
            order_count = cursor.fetchone()[0]
            
            # Check low stock products
            cursor.execute("SELECT COUNT(*) FROM products WHERE stock < 10")
            low_stock_count = cursor.fetchone()[0]
            
            # Check pending orders
            cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
            pending_orders = cursor.fetchone()[0]
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "database": db_status,
                "metrics": {
                    "users": user_count,
                    "products": product_count,
                    "orders": order_count,
                    "low_stock_products": low_stock_count,
                    "pending_orders": pending_orders
                },
                "status": "healthy" if db_status == "healthy" and pending_orders == 0 else "warning"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Health check failed: {str(e)}",
                "status": "unhealthy"
            }
    
    def get_user_info(self, user_id: int) -> Dict[str, Any]:
        """Get user information and order history."""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user_result = cursor.fetchone()
            
            if not user_result:
                return {"success": False, "error": "User not found"}
            
            user_info = dict(user_result)
            
            # Get user orders
            cursor.execute("""
                SELECT o.*, 
                       COUNT(oi.id) as item_count,
                       SUM(oi.quantity) as total_items
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.user_id = ?
                GROUP BY o.id
                ORDER BY o.created_at DESC
            """, (user_id,))
            
            orders = [dict(row) for row in cursor.fetchall()]
            
            user_info["orders"] = orders
            user_info["order_count"] = len(orders)
            
            return {"success": True, "user": user_info}
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get user info: {str(e)}"
            }
    
    def update_product_stock(self, product_id: int, stock_change: int) -> Dict[str, Any]:
        """Update product stock (positive to add, negative to remove)."""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("SELECT stock FROM products WHERE id = ?", (product_id,))
            product_result = cursor.fetchone()
            
            if not product_result:
                return {"success": False, "error": "Product not found"}
            
            current_stock = product_result["stock"]
            new_stock = current_stock + stock_change
            
            if new_stock < 0:
                return {"success": False, "error": "Stock cannot be negative"}
            
            cursor.execute(
                "UPDATE products SET stock = ? WHERE id = ?",
                (new_stock, product_id)
            )
            self.conn.commit()
            
            return {
                "success": True,
                "product_id": product_id,
                "old_stock": current_stock,
                "new_stock": new_stock,
                "stock_change": stock_change
            }
            
        except Exception as e:
            self.conn.rollback()
            return {
                "success": False,
                "error": f"Failed to update stock: {str(e)}"
            }
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

def demo():
    """Demonstrate all features of the trading system."""
    print("=" * 80)
    print("TRADITIONAL TRADING SYSTEM DEMO")
    print("=" * 80)
    print()
    
    # Initialize system
    system = TradingSystem("trading.db")
    print("✅ System initialized with SQLite database")
    print()
    
    # 1. Register users
    print("1. USER REGISTRATION")
    print("-" * 40)
    
    users = []
    for i in range(3):
        result = system.register_user(
            username=f"user{i+1}",
            email=f"user{i+1}@example.com",
            initial_balance=1500.0
        )
        if result["success"]:
            users.append(result["user_id"])
            print(f"   ✅ Registered user{i+1} (ID: {result['user_id']})")
        else:
            print(f"   ❌ Failed: {result['error']}")
    print()
    
    # 2. Add products
    print("2. PRODUCT INVENTORY")
    print("-" * 40)
    
    products = []
    product_data = [
        ("Laptop", "High-performance laptop", 999.99, 50, "electronics"),
        ("Mouse", "Wireless mouse", 29.99, 100, "electronics"),
        ("Keyboard", "Mechanical keyboard", 89.99, 75, "electronics"),
        ("Monitor", "27-inch 4K monitor", 499.99, 30, "electronics"),
        ("Headphones", "Noise-cancelling headphones", 199.99, 40, "audio")
    ]
    
    for name, desc, price, stock, category in product_data:
        result = system.add_product(name, desc, price, stock, category)
        if result["success"]:
            products.append(result["product_id"])
            print(f"   ✅ Added {name} (ID: {result['product_id']}) - ${price}")
        else:
            print(f"   ❌ Failed: {result['error']}")
    print()
    
    # 3. Create orders
    print("3. ORDER PROCESSING")
    print("-" * 40)
    
    orders = []
    order_items = [
        [{"product_id": products[0], "quantity": 1}, {"product_id": products[1], "quantity": 2}],
        [{"product_id": products[2], "quantity": 1}, {"product_id": products[3], "quantity": 1}],
        [{"product_id": products[4], "quantity": 3}]
    ]
    
    for i, items in enumerate(order_items):
        if i < len(users):
            result = system.create_order(users[i], items)
            if result["success"]:
                orders.append(result["order_id"])
                print(f"   ✅ Order {result['order_id']} created for user {users[i]} - Total: ${result['total_amount']:.2f}")
            else:
                print(f"   ❌ Failed: {result['error']}")
    print()
    
    # 4. Sales analytics
    print("4. SALES ANALYTICS")
    print("-" * 40)
    
    result = system.get_sales_summary(days=30)
    if result["success"]:
        print(f"   📊 Total Orders: {result['total_orders']}")
        print(f"   💰 Total Revenue: ${result['total_revenue']:.2f}")
        print(f"   📈 Average Order Value: ${result['avg_order_value']:.2f}")
        print()
        print("   Top Products:")
        for product in result["top_products"]:
            print(f"     • {product['name']}: {product['total_quantity']} units (${product['total_revenue']:.2f})")
    else:
        print(f"   ❌ Failed: {result['error']}")
    print()
    
    # 5. Health monitoring
    print("5. SYSTEM HEALTH CHECK")
    print("-" * 40)
    
    result = system.health_check()
    if result["success"]:
        print(f"   ✅ Database: {result['database']}")
        print(f"   📊 Metrics:")
        for key, value in result["metrics"].items():
            print(f"     • {key}: {value}")
        print(f"   🟢 Status: {result['status']}")
    else:
        print(f"   ❌ Failed: {result['error']}")
    print()
    
    # 6. Additional features
    print("6. ADDITIONAL FEATURES")
    print("-" * 40)
    
    # Get user info
    if users:
        result = system.get_user_info(users[0])
        if result["success"]:
            user = result["user"]
            print(f"   👤 User {user['username']}:")
            print(f"     • Balance: ${user['balance']:.2f}")
            print(f"     • Orders: {user['order_count']}")
    
    # Update stock
    if products:
        result = system.update_product_stock(products[0], -5)
        if result["success"]:
            print(f"   📦 Updated product {products[0]} stock:")
            print(f"     • Old: {result['old_stock']}")
            print(f"     • New: {result['new_stock']}")
            print(f"     • Change: {result['stock_change']}")
    
    print()
    print("=" * 80)
    print("DEMO COMPLETED SUCCESSFULLY")
    print("=" * 80)
    
    # Cleanup
    system.close()

if __name__ == "__main__":
    demo()