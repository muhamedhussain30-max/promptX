#!/usr/bin/env python3
"""
Deployment Verification Script
Run this to verify HuggingFace API is working correctly
"""
import sys
import os

def verify_environment():
    """Verify all required environment variables are set"""
    required_vars = ['HF_TOKEN', 'AI_PROVIDER']
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        return False
    
    print("✅ All required environment variables are set")
    return True

def verify_huggingface_sdk():
    """Verify huggingface_hub is installed and has correct version"""
    try:
        import huggingface_hub
        version = huggingface_hub.__version__
        print(f"✅ huggingface_hub version: {version}")
        
        # Check if version is >= 0.27.0
        major, minor, *_ = version.split('.')
        if int(major) == 0 and int(minor) < 27:
            print(f"⚠️  Warning: huggingface_hub version {version} is old. Recommended: >= 0.27.0")
            return False
        
        return True
    except ImportError:
        print("❌ huggingface_hub is not installed")
        return False
    except Exception as e:
        print(f"❌ Error checking huggingface_hub: {e}")
        return False

def verify_inference_client():
    """Verify InferenceClient can be imported and initialized"""
    try:
        from huggingface_hub import InferenceClient
        
        token = os.getenv('HF_TOKEN')
        if not token:
            print("❌ HF_TOKEN not set")
            return False
        
        # Try to initialize client (doesn't make API call)
        client = InferenceClient(api_key=token)
        print("✅ InferenceClient initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error initializing InferenceClient: {e}")
        return False

def main():
    print("=" * 60)
    print("PromptX Deployment Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Environment Variables", verify_environment),
        ("HuggingFace SDK", verify_huggingface_sdk),
        ("Inference Client", verify_inference_client),
    ]
    
    passed = 0
    failed = 0
    
    for name, check_func in checks:
        print(f"\n🔍 Checking: {name}")
        print("-" * 60)
        if check_func():
            passed += 1
        else:
            failed += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ All checks passed! Deployment is ready.")
        sys.exit(0)
    else:
        print(f"\n❌ {failed} check(s) failed. Please fix before deploying.")
        sys.exit(1)

if __name__ == "__main__":
    main()
