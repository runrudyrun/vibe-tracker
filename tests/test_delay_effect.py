#!/usr/bin/env python3
"""
Test delay effect implementation and LLM integration.

This tests:
1. DelayEffect creation and parameters
2. Audio processing performance
3. LLM generation of instruments with delay
4. Real-world usage scenarios
"""

import sys
import os
import numpy as np
import time
import wave

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llm_generator import LLMGenerator
from synthesis import Instrument
from effects import DelayEffect, create_effect_from_dict


def test_delay_effect_creation():
    """Test basic delay effect creation and parameters."""
    print("🔧 Testing DelayEffect creation...")
    
    # Test default creation
    delay = DelayEffect()
    assert delay.effect_type == "delay"
    assert delay.enabled == True
    
    # Test parameter defaults
    defaults = DelayEffect.get_default_params()
    expected_keys = ['delay_time', 'feedback', 'damping', 'wet_level', 'dry_level', 'enabled']
    for key in expected_keys:
        assert key in defaults, f"Missing default parameter: {key}"
    
    print(f"  ✅ Default parameters: {defaults}")
    
    # Test custom parameters
    custom_params = {
        'delay_time': 0.5,
        'feedback': 0.6,
        'wet_level': 0.4
    }
    delay_custom = DelayEffect(**custom_params)
    assert delay_custom.params['delay_time'] == 0.5
    assert delay_custom.params['feedback'] == 0.6
    
    print("  ✅ Custom parameters work correctly")
    
    # Test serialization
    delay_dict = delay_custom.to_dict()
    assert delay_dict['type'] == 'delay'
    assert delay_dict['delay_time'] == 0.5
    assert delay_dict['feedback'] == 0.6
    
    print("  ✅ Serialization works correctly")
    
    # Test deserialization
    delay_restored = DelayEffect.from_dict(delay_dict)
    assert delay_restored.params['delay_time'] == 0.5
    assert delay_restored.params['feedback'] == 0.6
    
    print("  ✅ Deserialization works correctly")
    
    return True


def test_delay_audio_processing():
    """Test delay effect audio processing."""
    print("\n🎵 Testing DelayEffect audio processing...")
    
    # Create delay with moderate settings
    delay = DelayEffect(
        delay_time=0.25,  # 250ms
        feedback=0.4,
        wet_level=0.3,
        dry_level=1.0
    )
    
    # Generate test audio (simple sine wave)
    sample_rate = 44100
    duration = 1.0  # 1 second
    frequency = 440  # A4
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    test_audio = np.sin(2 * np.pi * frequency * t) * 0.5
    
    # Process in chunks to simulate real-time
    chunk_size = 1024
    processed_chunks = []
    processing_times = []
    
    for i in range(0, len(test_audio), chunk_size):
        chunk = test_audio[i:i+chunk_size]
        if len(chunk) < chunk_size:
            # Pad last chunk
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
        
        start_time = time.perf_counter()
        processed_chunk = delay.process(chunk)
        end_time = time.perf_counter()
        
        processing_times.append((end_time - start_time) * 1000)  # ms
        processed_chunks.append(processed_chunk)
    
    # Analyze performance
    avg_time = np.mean(processing_times)
    max_time = np.max(processing_times)
    
    print(f"  📊 Performance: avg={avg_time:.2f}ms, max={max_time:.2f}ms")
    
    # Check performance requirements
    assert avg_time < 20, f"Average processing too slow: {avg_time:.2f}ms"
    assert max_time < 50, f"Peak processing too slow: {max_time:.2f}ms"
    
    # Analyze audio output
    full_output = np.concatenate(processed_chunks)[:len(test_audio)]
    
    # Check for reasonable output levels
    peak_level = np.max(np.abs(full_output))
    rms_level = np.sqrt(np.mean(full_output**2))
    
    print(f"  📊 Audio: peak={peak_level:.3f}, rms={rms_level:.3f}")
    
    # Should have some output but not clipping
    assert peak_level > 0.1, "Output too quiet"
    assert peak_level < 0.99, "Output clipping"
    
    # Save sample for manual inspection
    try:
        sample_audio = (full_output * 0.8).astype(np.float32)
        sample_audio_16 = (sample_audio * 32767).astype(np.int16)
        
        with wave.open("delay_test_sample.wav", 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(sample_audio_16.tobytes())
        
        print("  💾 Saved audio sample: delay_test_sample.wav")
    except Exception as e:
        print(f"  ⚠️  Could not save audio sample: {e}")
    
    print("  ✅ Audio processing works correctly")
    return True


def test_delay_factory_creation():
    """Test delay creation through factory function."""
    print("\n🏭 Testing DelayEffect factory creation...")
    
    # Test factory creation
    delay_data = {
        'type': 'delay',
        'delay_time': 0.375,
        'feedback': 0.5,
        'damping': 0.3,
        'wet_level': 0.4,
        'enabled': True
    }
    
    delay = create_effect_from_dict(delay_data)
    assert isinstance(delay, DelayEffect)
    assert delay.params['delay_time'] == 0.375
    assert delay.params['feedback'] == 0.5
    
    print("  ✅ Factory creation works correctly")
    return True


def test_llm_delay_generation():
    """Test LLM generation of instruments with delay."""
    print("\n🤖 Testing LLM delay generation...")
    
    try:
        generator = LLMGenerator()
        
        # Request instrument with delay
        prompt = "Create a guitar lead with rhythmic delay, feedback around 0.5, and quarter note timing"
        
        print(f"Sending prompt: '{prompt}'")
        composition_data, error = generator.generate_music_from_prompt(prompt)
        
        if error:
            print(f"❌ LLM Error: {error}")
            return False
        
        if not composition_data:
            print("❌ No composition generated")
            return False
        
        print("✅ LLM generated composition successfully")
        
        # Look for delay effects
        instruments = composition_data.get('instruments', [])
        delay_instruments = []
        
        for instrument_data in instruments:
            effects = instrument_data.get('effects', [])
            delay_effects = [e for e in effects if e.get('type') == 'delay']
            if delay_effects:
                delay_instruments.append({
                    'name': instrument_data.get('name'),
                    'delay': delay_effects[0],
                    'data': instrument_data
                })
        
        if delay_instruments:
            print(f"✅ Found {len(delay_instruments)} instruments with delay:")
            for inst in delay_instruments:
                delay = inst['delay']
                print(f"  • {inst['name']}: delay_time={delay.get('delay_time', 0.25)}, feedback={delay.get('feedback', 0.4)}")
            
            # Test creating the instrument
            inst_data = delay_instruments[0]['data']
            instrument = Instrument.from_dict(inst_data)
            print(f"  ✅ Created instrument with {len(instrument.effects)} effect(s)")
            
            # Quick audio test
            instrument.note_on("G3", velocity=0.7)
            buffer = instrument.process(1024)
            max_amp = np.max(np.abs(buffer))
            print(f"  📊 Audio test: max amplitude = {max_amp:.3f}")
            
            return True
        else:
            print("⚠️  No delay effects found in generated composition")
            print("Generated instruments:", [inst.get('name') for inst in instruments])
            return False
        
    except Exception as e:
        print(f"❌ LLM generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_delay_parameter_ranges():
    """Test delay effect with various parameter ranges."""
    print("\n🎛️  Testing DelayEffect parameter ranges...")
    
    test_cases = [
        # (delay_time, feedback, expected_stable)
        (0.1, 0.2, True),    # Short delay, low feedback
        (0.25, 0.5, True),   # Quarter note, medium feedback
        (0.5, 0.7, True),    # Half note, high feedback
        (1.0, 0.4, True),    # Long delay, medium feedback
        (0.125, 0.8, True),  # Eighth note, high feedback
    ]
    
    for delay_time, feedback, expected_stable in test_cases:
        print(f"  Testing delay_time={delay_time}, feedback={feedback}")
        
        delay = DelayEffect(
            delay_time=delay_time,
            feedback=feedback,
            wet_level=0.3
        )
        
        # Generate test signal
        test_signal = np.random.random(4096) * 0.1  # Quiet random signal
        
        # Process multiple times to check stability
        output = test_signal.copy()
        max_amplitudes = []
        
        for _ in range(10):  # 10 iterations
            output = delay.process(output)
            max_amplitudes.append(np.max(np.abs(output)))
        
        # Check if amplitude is growing (instability)
        final_amp = max_amplitudes[-1]
        initial_amp = max_amplitudes[0]
        
        is_stable = final_amp < initial_amp * 2  # Allow some growth but not runaway
        
        print(f"    Initial: {initial_amp:.3f}, Final: {final_amp:.3f}, Stable: {is_stable}")
        
        if expected_stable:
            assert is_stable, f"Delay became unstable with delay_time={delay_time}, feedback={feedback}"
    
    print("  ✅ All parameter ranges stable")
    return True


def main():
    """Run complete delay effect test suite."""
    print("🚀 Delay Effect Test Suite")
    print("=" * 40)
    
    tests = [
        test_delay_effect_creation,
        test_delay_audio_processing,
        test_delay_factory_creation,
        test_delay_parameter_ranges,
        test_llm_delay_generation,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All delay effect tests passed!")
        print("Delay effect is ready for use in compositions!")
    else:
        print("⚠️  Some tests failed - delay effect needs fixes")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
