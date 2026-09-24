#!/usr/bin/env python3
"""
Startup verification script - checks all dependencies before starting server
"""
import sys

def check_dependencies():
    """Verify critical dependencies are installed"""
    checks_passed = True
    
    # Check bcrypt
    try:
        import bcrypt
        print(f"✅ bcrypt version: {bcrypt.__version__}")
    except ImportError as e:
        print(f"❌ bcrypt not installed: {e}")
        checks_passed = False
    
    # Check fastapi
    try:
        import fastapi
        print(f"✅ fastapi version: {fastapi.__version__}")
    except ImportError as e:
        print(f"❌ fastapi not installed: {e}")
        checks_passed = False
    
    # Check sqlalchemy
    try:
        import sqlalchemy
        print(f"✅ sqlalchemy version: {sqlalchemy.__version__}")
    except ImportError as e:
        print(f"❌ sqlalchemy not installed: {e}")
        checks_passed = False
    
    # Check httpx
    try:
        import httpx
        print(f"✅ httpx version: {httpx.__version__}")
    except ImportError as e:
        print(f"❌ httpx not installed: {e}")
        checks_passed = False
    
    # Check huggingface_hub
    try:
        import huggingface_hub
        print(f"✅ huggingface_hub version: {huggingface_hub.__version__}")
    except ImportError as e:
        print(f"❌ huggingface_hub not installed: {e}")
        checks_passed = False
    
    return checks_passed

def test_password_hashing():
    """Test bcrypt password hashing"""
    try:
        import bcrypt
        password = "test123"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        verified = bcrypt.checkpw(password.encode(), hashed)
        if verified:
            print("✅ Password hashing works correctly")
            return True
        else:
            print("❌ Password verification failed")
            return False
    except Exception as e:
        print(f"❌ Password hashing error: {e}")
        return False

def check_database_url():
    """Check if DATABASE_URL is set"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    
    if db_url:
        # Hide credentials in output
        if "sqlite" in db_url:
            print(f"✅ Database URL: {db_url}")
        else:
            print(f"✅ Database URL: configured (PostgreSQL)")
        return True
    else:
        print("⚠️  DATABASE_URL not set, will use default SQLite")
        return True  # Not critical, has default

def main():
    print("=" * 60)
    print("PromptX Backend Startup Verification")
    print("=" * 60)
    print()
    
    all_passed = True
    
    print("Checking Dependencies...")
    print("-" * 60)
    if not check_dependencies():
        all_passed = False
    
    print()
    print("Testing Password Hashing...")
    print("-" * 60)
    if not test_password_hashing():
        all_passed = False
    
    print()
    print("Checking Environment...")
    print("-" * 60)
    check_database_url()
    
    print()
    print("=" * 60)
    if all_passed:
        print("✅ All checks passed! Server ready to start.")
        sys.exit(0)
    else:
        print("❌ Some checks failed. Please fix before starting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
