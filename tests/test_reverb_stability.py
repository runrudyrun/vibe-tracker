#!/usr/bin/env python3
"""
Reverb Stability Test - Diagnose instability and strange behavior.

This test specifically looks for:
1. Audio artifacts (clicks, pops, NaN values)
2. Memory leaks in delay buffers
3. Parameter changes causing instability
4. Buffer overflow/underflow issues
5. Feedback loop instability
6. Performance degradation over time
"""

import sys
import os
import numpy as np
import time

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from effects import ReverbEffect
from synthesis import Instrument


def test_reverb_artifacts():
    """Test for audio artifacts like clicks, pops, NaN values."""
    print("🔍 Testing for audio artifacts...")
    
    reverb = ReverbEffect(room_size=0.5, wet_level=0.3, dry_level=0.7)
    
    # Generate test signal
    sample_rate = 44100
    duration = 1.0  # 1 second
    num_samples = int(sample_rate * duration)
    
    # Create impulse (sudden signal change - prone to artifacts)
    test_signal = np.zeros(num_samples)
    test_signal[1000] = 1.0  # Sharp impulse
    test_signal[5000] = -0.5  # Negative impulse
    
    # Process through reverb
    output = reverb.process(test_signal)
    
    # Check for artifacts
    issues = []
    
    # Check for NaN or infinite values
    if np.any(np.isnan(output)):
        issues.append("NaN values detected")
    if np.any(np.isinf(output)):
        issues.append("Infinite values detected")
    
    # Check for excessive clipping
    clipped_samples = np.sum(np.abs(output) >= 0.99)
    if clipped_samples > num_samples * 0.01:  # More than 1% clipped
        issues.append(f"Excessive clipping: {clipped_samples} samples")
    
    # Check for sudden jumps (clicks/pops)
    diff = np.diff(output)
    max_jump = np.max(np.abs(diff))
    if max_jump > 0.5:  # Sudden jump > 0.5
        issues.append(f"Large audio jump detected: {max_jump:.3f}")
    
    # Check for DC offset
    dc_offset = np.mean(output)
    if abs(dc_offset) > 0.01:
        issues.append(f"DC offset detected: {dc_offset:.3f}")
    
    if issues:
        print(f"❌ Audio artifacts found:")
        for issue in issues:
            print(f"   • {issue}")
        return False
    else:
        print("✅ No audio artifacts detected")
        return True


def test_reverb_memory_stability():
    """Test for memory leaks and buffer stability."""
    print("🔍 Testing memory stability...")
    
    reverb = ReverbEffect(room_size=0.7, wet_level=0.4)
    
    # Process many buffers to check for memory issues
    buffer_size = 1024
    num_iterations = 1000
    
    # Generate test signal
    test_signal = 0.1 * np.random.randn(buffer_size)
    
    # Track buffer states
    initial_buffer_sizes = [len(buf) for buf in reverb.delay_buffers]
    
    for i in range(num_iterations):
        output = reverb.process(test_signal)
        
        # Check buffer integrity every 100 iterations
        if i % 100 == 0:
            current_buffer_sizes = [len(buf) for buf in reverb.delay_buffers]
            if current_buffer_sizes != initial_buffer_sizes:
                print(f"❌ Buffer size changed at iteration {i}")
                print(f"   Initial: {initial_buffer_sizes}")
                print(f"   Current: {current_buffer_sizes}")
                return False
            
            # Check for buffer corruption
            for j, buf in enumerate(reverb.delay_buffers):
                if np.any(np.isnan(buf)) or np.any(np.isinf(buf)):
                    print(f"❌ Buffer {j} corrupted at iteration {i}")
                    return False
    
    print("✅ Memory stability test passed")
    return True


def test_reverb_parameter_changes():
    """Test stability when parameters change during processing."""
    print("🔍 Testing parameter change stability...")
    
    reverb = ReverbEffect(room_size=0.3, wet_level=0.2)
    
    # Generate continuous test signal
    buffer_size = 512
    test_signal = 0.1 * np.sin(2 * np.pi * 440 * np.linspace(0, buffer_size/44100, buffer_size))
    
    issues = []
    
    # Test parameter changes
    parameter_tests = [
        ('room_size', [0.1, 0.5, 0.9, 0.2]),
        ('wet_level', [0.0, 0.5, 1.0, 0.3]),
        ('dry_level', [1.0, 0.5, 0.0, 0.7]),
        ('damping', [0.1, 0.8, 0.4, 0.5])
    ]
    
    for param_name, values in parameter_tests:
        for value in values:
            # Change parameter
            reverb.set_param(param_name, value)
            
            # Process audio
            try:
                output = reverb.process(test_signal)
                
                # Check for artifacts after parameter change
                if np.any(np.isnan(output)) or np.any(np.isinf(output)):
                    issues.append(f"NaN/Inf after setting {param_name}={value}")
                
                max_val = np.max(np.abs(output))
                if max_val > 2.0:  # Excessive amplitude
                    issues.append(f"Excessive amplitude ({max_val:.3f}) after setting {param_name}={value}")
                    
            except Exception as e:
                issues.append(f"Exception when setting {param_name}={value}: {e}")
    
    if issues:
        print(f"❌ Parameter change issues:")
        for issue in issues:
            print(f"   • {issue}")
        return False
    else:
        print("✅ Parameter change stability test passed")
        return True


def test_reverb_feedback_stability():
    """Test for feedback loop instability."""
    print("🔍 Testing feedback stability...")
    
    # Test with high feedback settings that might cause instability
    high_feedback_configs = [
        {'room_size': 0.9, 'wet_level': 0.8, 'damping': 0.1},
        {'room_size': 1.0, 'wet_level': 1.0, 'damping': 0.0},
        {'room_size': 0.8, 'wet_level': 0.9, 'damping': 0.2}
    ]
    
    issues = []
    
    for i, config in enumerate(high_feedback_configs):
        reverb = ReverbEffect(**config)
        
        # Generate impulse
        test_signal = np.zeros(8192)
        test_signal[100] = 0.5
        
        # Process and check for runaway feedback
        output = reverb.process(test_signal)
        
        max_amplitude = np.max(np.abs(output))
        if max_amplitude > 5.0:  # Runaway feedback
            issues.append(f"Config {i+1}: Runaway feedback (max={max_amplitude:.3f})")
        
        # Check for oscillation in tail
        tail = output[-1000:]  # Last 1000 samples
        if np.std(tail) > 0.1 and np.mean(np.abs(tail)) > 0.01:
            # High variance in tail suggests oscillation
            issues.append(f"Config {i+1}: Possible oscillation in reverb tail")
    
    if issues:
        print(f"❌ Feedback stability issues:")
        for issue in issues:
            print(f"   • {issue}")
        return False
    else:
        print("✅ Feedback stability test passed")
        return True


def test_reverb_performance_consistency():
    """Test for performance degradation over time."""
    print("🔍 Testing performance consistency...")
    
    reverb = ReverbEffect(room_size=0.6, wet_level=0.4)
    
    buffer_size = 1024
    test_signal = 0.1 * np.random.randn(buffer_size)
    
    # Measure processing times
    times = []
    num_measurements = 100
    
    for i in range(num_measurements):
        start_time = time.perf_counter()
        output = reverb.process(test_signal)
        end_time = time.perf_counter()
        
        times.append((end_time - start_time) * 1000)  # Convert to ms
    
    # Analyze timing consistency
    mean_time = np.mean(times)
    std_time = np.std(times)
    max_time = np.max(times)
    min_time = np.min(times)
    
    print(f"   Processing time stats:")
    print(f"   • Mean: {mean_time:.3f}ms")
    print(f"   • Std:  {std_time:.3f}ms")
    print(f"   • Min:  {min_time:.3f}ms")
    print(f"   • Max:  {max_time:.3f}ms")
    
    # Check for concerning patterns
    issues = []
    
    if std_time > mean_time * 0.5:  # High variance
        issues.append(f"High timing variance: {std_time:.3f}ms")
    
    if max_time > mean_time * 3:  # Occasional very slow processing
        issues.append(f"Occasional slow processing: {max_time:.3f}ms")
    
    # Check for trend (performance degradation)
    first_half = np.mean(times[:50])
    second_half = np.mean(times[50:])
    if second_half > first_half * 1.2:  # 20% slower
        issues.append(f"Performance degradation: {first_half:.3f}ms → {second_half:.3f}ms")
    
    if issues:
        print(f"❌ Performance issues:")
        for issue in issues:
            print(f"   • {issue}")
        return False
    else:
        print("✅ Performance consistency test passed")
        return True


def test_instrument_reverb_integration():
    """Test reverb stability within instrument context."""
    print("🔍 Testing instrument integration stability...")
    
    # Create instrument with reverb
    instrument_data = {
        "name": "test_reverb",
        "oscillators": [{"waveform": "sine", "amplitude": 0.8}],
        "attack": 0.01, "decay": 0.1, "sustain_level": 0.7, "release": 0.2,
        "effects": [{"type": "reverb", "room_size": 0.6, "wet_level": 0.4}]
    }
    
    instrument = Instrument.from_dict(instrument_data)
    
    issues = []
    
    # Test multiple note triggering (polyphony with reverb)
    notes = ["C4", "E4", "G4", "C5"]
    for note in notes:
        instrument.note_on(note, velocity=0.7)
    
    # Process several buffers
    for i in range(50):
        try:
            output = instrument.process(1024)
            
            # Check for artifacts
            if np.any(np.isnan(output)) or np.any(np.isinf(output)):
                issues.append(f"NaN/Inf in instrument output at buffer {i}")
            
            max_amp = np.max(np.abs(output))
            if max_amp > 2.0:
                issues.append(f"Excessive amplitude in instrument: {max_amp:.3f}")
                
        except Exception as e:
            issues.append(f"Exception in instrument processing: {e}")
    
    if issues:
        print(f"❌ Instrument integration issues:")
        for issue in issues:
            print(f"   • {issue}")
        return False
    else:
        print("✅ Instrument integration test passed")
        return True


def main():
    """Run all reverb stability tests."""
    print("🚀 Reverb Stability Diagnostic Tests")
    print("=" * 50)
    
    tests = [
        test_reverb_artifacts,
        test_reverb_memory_stability,
        test_reverb_parameter_changes,
        test_reverb_feedback_stability,
        test_reverb_performance_consistency,
        test_instrument_reverb_integration
    ]
    
    results = []
    
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
            print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("📊 Test Summary:")
    print(f"   Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All stability tests passed!")
        print("   Reverb appears to be stable.")
    else:
        print("⚠️  Some stability issues detected!")
        print("   Check the detailed output above for specific problems.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
