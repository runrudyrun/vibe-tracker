#!/usr/bin/env python3
"""
Detailed analysis of reverb audio jumps to identify the root cause.
"""

import sys
import os
import numpy as np

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from effects import ReverbEffect


def analyze_reverb_response():
    """Analyze reverb response to impulse to find jump sources."""
    print("🔍 Analyzing reverb impulse response...")
    
    reverb = ReverbEffect(room_size=0.5, wet_level=0.3, dry_level=0.7)
    
    # Create impulse signal
    num_samples = 8192
    impulse = np.zeros(num_samples)
    impulse[1000] = 1.0  # Single impulse
    
    # Process through reverb
    output = reverb.process(impulse)
    
    # Analyze the response
    print(f"Input impulse amplitude: {impulse[1000]}")
    print(f"Max output amplitude: {np.max(np.abs(output)):.6f}")
    print(f"Output at impulse position: {output[1000]:.6f}")
    
    # Find the largest jumps
    diff = np.diff(output)
    abs_diff = np.abs(diff)
    max_jump_idx = np.argmax(abs_diff)
    max_jump = abs_diff[max_jump_idx]
    
    print(f"Largest jump: {max_jump:.6f} at sample {max_jump_idx}")
    print(f"Jump from {output[max_jump_idx]:.6f} to {output[max_jump_idx+1]:.6f}")
    
    # Look at the context around the jump
    start_idx = max(0, max_jump_idx - 10)
    end_idx = min(len(output), max_jump_idx + 10)
    
    print(f"\nContext around largest jump (samples {start_idx}-{end_idx}):")
    for i in range(start_idx, end_idx):
        marker = " <-- JUMP" if i == max_jump_idx else ""
        print(f"  Sample {i:4d}: {output[i]:8.6f}{marker}")
    
    # Check if the jump is at the impulse position
    if abs(max_jump_idx - 1000) < 5:
        print("\n⚠️  Jump occurs near the impulse - this might be expected behavior")
    else:
        print(f"\n❌ Jump occurs away from impulse (offset: {max_jump_idx - 1000})")
    
    return output, max_jump


def analyze_step_response():
    """Analyze response to step function."""
    print("\n🔍 Analyzing reverb step response...")
    
    reverb = ReverbEffect(room_size=0.5, wet_level=0.3, dry_level=0.7)
    
    # Create step signal
    num_samples = 4096
    step = np.zeros(num_samples)
    step[1000:] = 0.5  # Step from 0 to 0.5
    
    # Process through reverb
    output = reverb.process(step)
    
    # Find jumps
    diff = np.diff(output)
    abs_diff = np.abs(diff)
    large_jumps = np.where(abs_diff > 0.1)[0]
    
    print(f"Found {len(large_jumps)} large jumps (>0.1)")
    
    for i, jump_idx in enumerate(large_jumps[:5]):  # Show first 5
        jump_size = abs_diff[jump_idx]
        print(f"  Jump {i+1}: {jump_size:.6f} at sample {jump_idx}")
        print(f"    From {output[jump_idx]:.6f} to {output[jump_idx+1]:.6f}")
    
    return output


def analyze_continuous_signal():
    """Analyze response to continuous signal."""
    print("\n🔍 Analyzing reverb with continuous signal...")
    
    reverb = ReverbEffect(room_size=0.5, wet_level=0.3, dry_level=0.7)
    
    # Create sine wave
    num_samples = 4096
    frequency = 440  # A4
    sample_rate = 44100
    t = np.linspace(0, num_samples/sample_rate, num_samples, False)
    sine_wave = 0.1 * np.sin(2 * np.pi * frequency * t)
    
    # Process through reverb
    output = reverb.process(sine_wave)
    
    # Find jumps
    diff = np.diff(output)
    abs_diff = np.abs(diff)
    max_jump = np.max(abs_diff)
    
    print(f"Max jump in continuous signal: {max_jump:.6f}")
    
    # Expected max jump for sine wave
    max_sine_diff = np.max(np.abs(np.diff(sine_wave)))
    print(f"Max jump in original sine: {max_sine_diff:.6f}")
    
    if max_jump > max_sine_diff * 5:  # 5x larger than input
        print("❌ Reverb amplifies signal discontinuities significantly")
    else:
        print("✅ Reverb jump amplification seems reasonable")
    
    return output


def test_different_parameters():
    """Test different reverb parameters to isolate the issue."""
    print("\n🔍 Testing different reverb parameters...")
    
    # Test configurations
    configs = [
        {"room_size": 0.1, "wet_level": 0.1, "dry_level": 0.9, "name": "minimal"},
        {"room_size": 0.5, "wet_level": 0.3, "dry_level": 0.7, "name": "moderate"},
        {"room_size": 0.9, "wet_level": 0.8, "dry_level": 0.2, "name": "extreme"},
        {"room_size": 0.0, "wet_level": 0.0, "dry_level": 1.0, "name": "dry_only"},
    ]
    
    # Test signal
    num_samples = 2048
    impulse = np.zeros(num_samples)
    impulse[500] = 1.0
    
    for config in configs:
        name = config.pop("name")
        reverb = ReverbEffect(**config)
        
        output = reverb.process(impulse)
        diff = np.abs(np.diff(output))
        max_jump = np.max(diff)
        
        print(f"  {name:12s}: max jump = {max_jump:.6f}")
        
        if max_jump > 0.5:
            print(f"    ❌ {name} configuration causes large jumps")
        else:
            print(f"    ✅ {name} configuration seems stable")


def main():
    """Run detailed reverb analysis."""
    print("🚀 Detailed Reverb Jump Analysis")
    print("=" * 50)
    
    try:
        # Run all analyses
        impulse_output, max_jump = analyze_reverb_response()
        step_output = analyze_step_response()
        continuous_output = analyze_continuous_signal()
        test_different_parameters()
        
        print("\n📊 Analysis Summary:")
        print(f"   Largest detected jump: {max_jump:.6f}")
        
        if max_jump > 0.5:
            print("   ❌ Large jumps detected - reverb needs further fixes")
            print("\n💡 Possible causes:")
            print("   • Delay buffer initialization issues")
            print("   • Feedback coefficient too high")
            print("   • Missing interpolation in delay lines")
            print("   • Sudden parameter changes")
        else:
            print("   ✅ Jumps within acceptable range")
        
        print("\n📈 Numerical analysis complete - no plotting available")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
