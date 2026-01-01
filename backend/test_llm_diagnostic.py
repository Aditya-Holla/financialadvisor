"""Diagnostic script to check why LLM is not available.

Run with: python test_llm_diagnostic.py
(Ensure you're in the backend directory with venv activated)
"""

import sys
from app.config import get_settings
from app.integrations.llm import LLMIntegration

def main():
    print("=" * 60)
    print("LLM Diagnostic Check")
    print("=" * 60)
    
    # Check settings
    settings = get_settings()
    print(f"\n1. Settings Check:")
    print(f"   LLM_API_KEY configured: {'Yes' if settings.LLM_API_KEY else 'No'}")
    if settings.LLM_API_KEY:
        key_preview = settings.LLM_API_KEY[:20] + "..." if len(settings.LLM_API_KEY) > 20 else settings.LLM_API_KEY
        print(f"   API Key preview: {key_preview}")
        if "your-" in settings.LLM_API_KEY.lower() or "placeholder" in settings.LLM_API_KEY.lower():
            print(f"   ⚠ WARNING: API key looks like a placeholder!")
    else:
        print(f"   ✗ LLM_API_KEY is None or empty")
    
    print(f"   LLM_MODEL: {settings.LLM_MODEL}")
    
    # Check LLM integration
    print(f"\n2. LLM Integration Check:")
    llm = LLMIntegration()
    print(f"   Client initialized: {'Yes' if llm.client else 'No'}")
    print(f"   is_available(): {llm.is_available()}")
    
    # Check OpenAI package
    print(f"\n3. Package Check:")
    try:
        from openai import AsyncOpenAI
        print(f"   ✓ OpenAI package installed")
        # Try to get version
        try:
            import openai
            print(f"   Version: {openai.__version__}")
        except:
            print(f"   Version: (could not determine)")
    except ImportError:
        print(f"   ✗ OpenAI package NOT installed")
        print(f"   Install with: pip install openai>=1.0.0")
    
    # Try to create client manually
    print(f"\n4. Manual Client Test:")
    if settings.LLM_API_KEY:
        try:
            from openai import AsyncOpenAI
            test_client = AsyncOpenAI(api_key=settings.LLM_API_KEY)
            print(f"   ✓ Successfully created OpenAI client")
        except Exception as e:
            print(f"   ✗ Failed to create client: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
    else:
        print(f"   ⚠ Skipped (no API key)")
    
    # Check .env file
    print(f"\n5. Environment File Check:")
    import os
    from pathlib import Path
    backend_dir = Path(__file__).parent
    env_file = backend_dir / ".env"
    env_example = backend_dir / ".env.example"
    
    print(f"   .env file exists: {env_file.exists()}")
    if env_file.exists():
        print(f"   .env path: {env_file.resolve()}")
        # Check if LLM_API_KEY is in .env
        try:
            with open(env_file, 'r') as f:
                env_content = f.read()
                if "LLM_API_KEY" in env_content:
                    print(f"   ✓ LLM_API_KEY found in .env")
                    # Check if it's a placeholder
                    for line in env_content.split('\n'):
                        if 'LLM_API_KEY' in line and '=' in line:
                            value = line.split('=', 1)[1].strip()
                            if "your-" in value.lower() or "placeholder" in value.lower():
                                print(f"   ⚠ WARNING: LLM_API_KEY in .env looks like a placeholder!")
                            break
                else:
                    print(f"   ✗ LLM_API_KEY not found in .env")
        except Exception as e:
            print(f"   ⚠ Could not read .env: {str(e)}")
    else:
        print(f"   ✗ .env file not found at {env_file.resolve()}")
        if env_example.exists():
            print(f"   ℹ .env.example exists - copy it to .env and add your API key")
    
    print(f"\n" + "=" * 60)
    print("\nRecommendations:")
    if not settings.LLM_API_KEY:
        print("1. Add LLM_API_KEY to your .env file")
        print("2. Get API key from: https://platform.openai.com/api-keys")
    elif not llm.client:
        print("1. Check if OpenAI package is installed: pip install openai>=1.0.0")
        print("2. Verify API key is valid (not a placeholder)")
    else:
        print("✓ LLM should be working! If tests still fail, check logs for errors.")
    print()

if __name__ == "__main__":
    main()

