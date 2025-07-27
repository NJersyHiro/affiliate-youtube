#!/usr/bin/env python3
"""Test script to verify basic setup without external dependencies."""

import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test basic imports without external dependencies."""
    print("Testing basic imports...")
    
    try:
        # Test logger (with optional colorlog)
        from utils.logger import setup_logger, get_logger
        print("✓ Logger module imported successfully")
        
        # Test exceptions
        from utils.exceptions import YouTubeShortsGeneratorError
        print("✓ Exceptions module imported successfully")
        
        # Test error handler
        from utils.error_handler import dev_error_logger
        print("✓ Error handler module imported successfully")
        
        # Test models
        from models.script import Script, ScriptStyle
        from models.audio import AudioClip, AudioSettings
        from models.video import VideoClip, VideoSettings
        from models.project import Project, ProjectStatus
        print("✓ All models imported successfully")
        
        print("\nBasic imports test passed! ✅")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_logger():
    """Test logger functionality."""
    print("\nTesting logger functionality...")
    
    try:
        from utils.logger import setup_logger
        
        # Test logger setup
        logger = setup_logger(name="test_logger", level="INFO")
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        
        print("✓ Logger functionality test passed")
        return True
        
    except Exception as e:
        print(f"✗ Logger test failed: {e}")
        return False

def test_error_logging():
    """Test error logging functionality."""
    print("\nTesting error logging...")
    
    try:
        from utils.error_handler import dev_error_logger
        
        # Test error logging
        dev_error_logger.log_error(
            module="TestModule",
            error_type="TestError",
            description="This is a test error",
            solution="No action needed - this is just a test"
        )
        
        print("✓ Error logging test passed")
        return True
        
    except Exception as e:
        print(f"✗ Error logging test failed: {e}")
        return False

def test_models():
    """Test model creation."""
    print("\nTesting model creation...")
    
    try:
        from models.script import Script, ScriptSegment, ScriptStyle
        from models.project import Project
        
        # Create a test script
        script = Script(
            service_name="Test Service",
            affiliate_url="https://example.com",
            style=ScriptStyle.HUMOROUS
        )
        
        # Add a segment
        segment = ScriptSegment(
            text="This is a test segment",
            duration=5.0,
            visual_description="Test visuals"
        )
        script.add_segment(segment)
        
        # Create a test project
        project = Project(
            name="Test Project",
            service_name="Test Service",
            affiliate_url="https://example.com"
        )
        project.script = script
        
        print(f"✓ Created script with {len(script.segments)} segment(s)")
        print(f"✓ Created project: {project.name}")
        print("✓ Model creation test passed")
        return True
        
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("YouTube Shorts Generator - Setup Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_logger,
        test_error_logging,
        test_models
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 40)
    print(f"Tests completed: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n✅ All tests passed! The basic setup is working correctly.")
        print("\nNext steps:")
        print("1. Install requirements: pip install -r requirements.txt")
        print("2. Set up your .env file with API keys")
        print("3. Run the full application")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        print("\nNote: This test only checks basic functionality.")
        print("External dependencies (yaml, google-generativeai, etc.) need to be installed.")

if __name__ == "__main__":
    main()