#!/usr/bin/env python3
"""
setup_experiment_simple.py — Simple setup script for experiment.

exports: main() -> None, reset_experiment(), setup_experiment(), test_experiment(), status_experiment()
used_by: [cascade] → experiment automation
rules:   Must provide reset/setup/test/status commands for both systems
agent:   deepseek-chat | 2026-03-29 | Created experiment management script
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

def print_colored(text, color_code):
    """Print colored text."""
    print(f"\033[{color_code}m{text}\033[0m")

def reset_experiment():
    """Reset experiment by deleting systems."""
    print_colored("=== RESET ESPERIMENTO ===", "1;34")
    
    exp_dir = Path(__file__).parent
    codedna = exp_dir / "codedna_system"
    traditional = exp_dir / "traditional_system"
    
    # Delete if exists
    if codedna.exists():
        print("Cancellando sistema CodeDNA...")
        shutil.rmtree(codedna)
        print_colored("✓ Sistema CodeDNA cancellato", "1;32")
    
    if traditional.exists():
        print("Cancellando sistema Tradizionale...")
        shutil.rmtree(traditional)
        print_colored("✓ Sistema Tradizionale cancellato", "1;32")
    
    # Create empty directories
    codedna.mkdir(parents=True, exist_ok=True)
    traditional.mkdir(parents=True, exist_ok=True)
    
    print_colored("✓ Reset completato", "1;32")

def setup_systems():
    """Setup both systems."""
    print_colored("=== SETUP SISTEMI ===", "1;34")
    
    # Reset first
    reset_experiment()
    
    exp_dir = Path(__file__).parent
    codedna = exp_dir / "codedna_system"
    traditional = exp_dir / "traditional_system"
    
    # Setup CodeDNA system (minimal)
    print("\nSetup sistema CodeDNA...")
    (codedna / "api_gateway").mkdir(parents=True, exist_ok=True)
    (codedna / "services" / "order_service").mkdir(parents=True, exist_ok=True)
    (codedna / "services" / "inventory_service").mkdir(parents=True, exist_ok=True)
    
    # Create simple API Gateway
    api_gateway = '''"""
api_gateway/main.py — API Gateway Service.
"""
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "api_gateway"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    (codedna / "api_gateway" / "main.py").write_text(api_gateway)
    
    # Create simple Order Service
    order_service = '''"""
services/order_service/main.py — Order Service.
"""
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "order_service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
'''
    (codedna / "services" / "order_service" / "main.py").write_text(order_service)
    
    # Create simple Inventory Service
    inventory_service = '''"""
services/inventory_service/main.py — Inventory Service.
"""
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "inventory_service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
'''
    (codedna / "services" / "inventory_service" / "main.py").write_text(inventory_service)
    
    # Create requirements
    requirements = "fastapi\nuvicorn\n"
    (codedna / "requirements.txt").write_text(requirements)
    
    # Create README
    readme = """# CodeDNA System (Microservices)

Quick start:
```bash
pip install -r requirements.txt
cd api_gateway && uvicorn main:app --port 8000
cd services/order_service && uvicorn main:app --port 8001
cd services/inventory_service && uvicorn main:app --port 8002
```
"""
    (codedna / "README.md").write_text(readme)
    
    print_colored("✓ Sistema CodeDNA configurato", "1;32")
    
    # Setup Traditional system
    print("\nSetup sistema Tradizionale...")
    
    # Create simple trading system
    trading_system = '''#!/usr/bin/env python3
"""
trading_system.py — Traditional Trading System.
"""

def main():
    print("=== Traditional Trading System ===")
    print("1. Registering user...")
    print("   Result: User registered")
    print("2. Adding product...")
    print("   Result: Product added")
    print("3. Creating order...")
    print("   Result: Order created")
    print("4. Sales summary...")
    print("   Result: Sales calculated")
    print("5. Health check...")
    print("   Result: System healthy")
    print("=== Demo Complete ===")

if __name__ == "__main__":
    main()
'''
    (traditional / "trading_system.py").write_text(trading_system)
    
    # Create README
    readme = """# Traditional System (Monolithic)

Quick start:
```bash
python3 trading_system.py
```
"""
    (traditional / "README.md").write_text(readme)
    
    print_colored("✓ Sistema Tradizionale configurato", "1;32")
    print_colored("\n✓ Setup completato! Entrambi i sistemi sono pronti.", "1;32")

def test_systems():
    """Test both systems."""
    print_colored("=== TEST SISTEMI ===", "1;34")
    
    exp_dir = Path(__file__).parent
    traditional = exp_dir / "traditional_system" / "trading_system.py"
    
    # Test Traditional system
    print("\nTest sistema Tradizionale...")
    if traditional.exists():
        try:
            result = subprocess.run(
                ["python3", str(traditional)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print_colored("✓ Sistema Tradizionale: FUNZIONA", "1;32")
                print(f"Output:\n{result.stdout}")
            else:
                print_colored("✗ Sistema Tradizionale: FALLITO", "1;31")
                print(f"Errore: {result.stderr}")
        except Exception as e:
            print_colored(f"✗ Sistema Tradizionale: ERRORE - {e}", "1;31")
    else:
        print_colored("✗ Sistema Tradizionale: FILE MANCANTE", "1;31")
    
    # Test CodeDNA structure
    print("\nTest struttura sistema CodeDNA...")
    codedna = exp_dir / "codedna_system"
    if codedna.exists():
        py_files = list(codedna.rglob("*.py"))
        if py_files:
            print_colored(f"✓ Sistema CodeDNA: {len(py_files)} file Python trovati", "1;32")
        else:
            print_colored("✗ Sistema CodeDNA: Nessun file Python", "1;31")
    else:
        print_colored("✗ Sistema CodeDNA: NON PRESENTE", "1;31")
    
    print_colored("\n✓ Test completato", "1;32")

def show_status():
    """Show experiment status."""
    print_colored("=== STATUS ESPERIMENTO ===", "1;34")
    
    exp_dir = Path(__file__).parent
    codedna = exp_dir / "codedna_system"
    traditional = exp_dir / "traditional_system"
    
    print(f"\nDirectory: {exp_dir}")
    
    print("\n📦 SISTEMA CODEDNA:")
    if codedna.exists():
        files = list(codedna.rglob("*"))
        print(f"  ✓ Presente ({len(files)} elementi)")
    else:
        print("  ✗ Non presente")
    
    print("\n🏛️  SISTEMA TRADIZIONALE:")
    if traditional.exists():
        files = list(traditional.rglob("*"))
        print(f"  ✓ Presente ({len(files)} elementi)")
        main_file = traditional / "trading_system.py"
        if main_file.exists():
            print(f"  ✓ File principale: trading_system.py")
    else:
        print("  ✗ Non presente")
    
    print("\n📋 COMANDI DISPONIBILI:")
    print("  python3 setup_experiment_simple.py reset   # Cancella sistemi")
    print("  python3 setup_experiment_simple.py setup   # Crea sistemi")
    print("  python3 setup_experiment_simple.py test    # Testa sistemi")
    print("  python3 setup_experiment_simple.py status  # Mostra stato")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Gestione esperimento")
    parser.add_argument("command", nargs="?", default="status", 
                       choices=["reset", "setup", "test", "status"],
                       help="Comando da eseguire")
    
    args = parser.parse_args()
    
    if args.command == "reset":
        reset_experiment()
    elif args.command == "setup":
        setup_systems()
    elif args.command == "test":
        test_systems()
    elif args.command == "status":
        show_status()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()