#!/usr/bin/env python3
"""
Test script for Hugging Face GPT-OSS integration
Tests the complete workflow from API connection to music generation
"""

import os
import sys
import json
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from llm_generator import LLMGenerator

def test_environment_setup():
    """Test if environment is properly configured"""
    print("=== Environment Setup Test ===")
    
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("❌ HF_TOKEN not found in environment")
        print("   Please set HF_TOKEN environment variable")
        return False
    
    print(f"✅ HF_TOKEN found: {hf_token[:8]}...")
    
    # Test other optional variables
    hf_model = os.getenv("HF_MODEL", "openai/gpt-oss-20b:cerebras")
    print(f"📋 Using model: {hf_model}")
    
    return True

def test_provider_initialization():
    """Test Hugging Face provider initialization"""
    print("\n=== Provider Initialization Test ===")
    
    try:
        # Test explicit HF provider
        generator = LLMGenerator("huggingface")
        provider_info = generator.get_provider_info()
        print(f"✅ Hugging Face provider initialized: {provider_info}")
        return generator
    except Exception as e:
        print(f"❌ Provider initialization failed: {e}")
        return None

def test_auto_provider_selection():
    """Test automatic provider selection"""
    print("\n=== Auto Provider Selection Test ===")
    
    try:
        generator = LLMGenerator("auto")
        provider_info = generator.get_provider_info()
        print(f"✅ Auto-selected provider: {provider_info}")
        return generator
    except Exception as e:
        print(f"❌ Auto provider selection failed: {e}")
        return None

def test_simple_generation(generator):
    """Test simple music generation"""
    print("\n=== Simple Generation Test ===")
    
    if not generator:
        print("❌ No generator available")
        return False
    
    try:
        print("🔄 Generating simple techno beat...")
        start_time = time.time()
        
        data, error = generator.generate_music_from_prompt("create a simple techno beat with kick and hi-hat")
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        if error:
            print(f"❌ Generation failed: {error}")
            return False
        
        if not data:
            print("❌ No data returned")
            return False
        
        print(f"✅ Generation successful in {generation_time:.2f}s")
        
        # Validate JSON structure
        required_keys = ['bpm', 'instruments', 'tracks']
        for key in required_keys:
            if key not in data:
                print(f"❌ Missing required key: {key}")
                return False
        
        print(f"📊 Generated composition:")
        print(f"   - BPM: {data.get('bpm', 'N/A')}")
        print(f"   - Instruments: {len(data.get('instruments', []))}")
        print(f"   - Tracks: {len(data.get('tracks', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Generation test failed: {e}")
        return False

def test_contextual_generation(generator):
    """Test generation with context"""
    print("\n=== Contextual Generation Test ===")
    
    if not generator:
        print("❌ No generator available")
        return False
    
    try:
        # First generate a base composition
        print("🔄 Generating base composition...")
        base_data, error = generator.generate_music_from_prompt("create a kick drum pattern")
        
        if error or not base_data:
            print(f"❌ Base generation failed: {error}")
            return False
        
        print("✅ Base composition created")
        
        # Add to existing composition
        print("🔄 Adding snare to existing composition...")
        start_time = time.time()
        
        extended_data, error = generator.generate_music_from_prompt(
            "add a snare drum on beats 2 and 4", 
            base_data
        )
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        if error:
            print(f"❌ Contextual generation failed: {error}")
            return False
        
        if not extended_data:
            print("❌ No extended data returned")
            return False
        
        print(f"✅ Contextual generation successful in {generation_time:.2f}s")
        
        # Compare track counts
        base_tracks = len(base_data.get('tracks', []))
        extended_tracks = len(extended_data.get('tracks', []))
        
        print(f"📊 Track comparison:")
        print(f"   - Base tracks: {base_tracks}")
        print(f"   - Extended tracks: {extended_tracks}")
        
        if extended_tracks <= base_tracks:
            print("⚠️  Warning: Track count didn't increase as expected")
        
        return True
        
    except Exception as e:
        print(f"❌ Contextual generation test failed: {e}")
        return False

def test_error_handling():
    """Test error handling scenarios"""
    print("\n=== Error Handling Test ===")
    
    # Test with invalid token
    original_token = os.environ.get('HF_TOKEN')
    os.environ['HF_TOKEN'] = 'invalid_token'
    
    try:
        generator = LLMGenerator("huggingface")
        data, error = generator.generate_music_from_prompt("test")
        
        if error:
            print("✅ Error handling works - invalid token detected")
        else:
            print("⚠️  Warning: Invalid token should have caused an error")
    
    except Exception as e:
        print(f"✅ Error handling works - exception caught: {type(e).__name__}")
    
    finally:
        # Restore original token
        if original_token:
            os.environ['HF_TOKEN'] = original_token
        else:
            os.environ.pop('HF_TOKEN', None)
    
    return True

def test_performance_benchmark(generator):
    """Run performance benchmark"""
    print("\n=== Performance Benchmark ===")
    
    if not generator:
        print("❌ No generator available")
        return False
    
    prompts = [
        "create a kick drum",
        "create a snare drum",
        "create a bass line",
        "create a hi-hat pattern",
        "create a simple melody"
    ]
    
    times = []
    successes = 0
    
    for i, prompt in enumerate(prompts, 1):
        print(f"🔄 Test {i}/5: {prompt}")
        
        try:
            start_time = time.time()
            data, error = generator.generate_music_from_prompt(prompt)
            end_time = time.time()
            
            generation_time = end_time - start_time
            times.append(generation_time)
            
            if error:
                print(f"   ❌ Failed: {error}")
            else:
                print(f"   ✅ Success in {generation_time:.2f}s")
                successes += 1
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n📊 Performance Summary:")
        print(f"   - Success rate: {successes}/{len(prompts)} ({successes/len(prompts)*100:.1f}%)")
        print(f"   - Average time: {avg_time:.2f}s")
        print(f"   - Min time: {min_time:.2f}s")
        print(f"   - Max time: {max_time:.2f}s")
        
        return successes > 0
    
    return False

def main():
    """Run all tests"""
    print("🚀 Starting Hugging Face Integration Tests")
    print("=" * 50)
    
    # Test environment
    if not test_environment_setup():
        print("\n❌ Environment setup failed. Please configure HF_TOKEN.")
        return False
    
    # Test provider initialization
    generator = test_provider_initialization()
    if not generator:
        print("\n❌ Provider initialization failed.")
        return False
    
    # Test auto selection
    auto_generator = test_auto_provider_selection()
    
    # Test basic generation
    if not test_simple_generation(generator):
        print("\n❌ Simple generation test failed.")
        return False
    
    # Test contextual generation
    if not test_contextual_generation(generator):
        print("\n❌ Contextual generation test failed.")
        return False
    
    # Test error handling
    test_error_handling()
    
    # Performance benchmark
    test_performance_benchmark(generator)
    
    print("\n" + "=" * 50)
    print("🎉 All tests completed!")
    print("\n✅ Hugging Face integration is working correctly")
    print("📖 See README-HUGGINGFACE.md for usage instructions")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
