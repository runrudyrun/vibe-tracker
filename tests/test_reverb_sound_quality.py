#!/usr/bin/env python3
"""
Reverb Sound Quality Analysis - Diagnose what makes the reverb sound "strange".

This test analyzes:
1. Frequency response characteristics
2. Reverb tail behavior
3. Early reflections vs late reverb
4. Metallic/artificial artifacts
5. Comparison with expected reverb behavior
"""

import sys
import os
import numpy as np
import time

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from effects import ReverbEffect
from synthesis import Instrument


def analyze_frequency_response():
    """Analyze how reverb affects different frequencies."""
    print("🔍 Analyzing frequency response...")
    
    reverb = ReverbEffect(room_size=0.5, wet_level=0.5, dry_level=0.5)
    
    sample_rate = 44100
    duration = 1.0
    num_samples = int(sample_rate * duration)
    
    # Test different frequencies
    test_frequencies = [100, 200, 440, 880, 2000, 4000, 8000]  # Hz
    
    for freq in test_frequencies:
        # Generate sine wave
        t = np.linspace(0, duration, num_samples, False)
        sine_wave = 0.1 * np.sin(2 * np.pi * freq * t)
        
        # Process through reverb
        reverb_output = reverb.process(sine_wave.copy())
        
        # Analyze the result
        input_rms = np.sqrt(np.mean(sine_wave**2))
        output_rms = np.sqrt(np.mean(reverb_output**2))
        
        gain_db = 20 * np.log10(output_rms / input_rms) if input_rms > 0 else -100
        
        print(f"  {freq:4d} Hz: {gain_db:+6.2f} dB")
        
        # Check for obvious artifacts
        if gain_db > 6:  # More than 6dB gain is suspicious
            print(f"    ⚠️  Excessive gain at {freq} Hz")
        elif gain_db < -20:  # More than 20dB loss is suspicious
            print(f"    ⚠️  Excessive loss at {freq} Hz")


def analyze_reverb_tail():
    """Analyze the reverb tail characteristics."""
    print("\n🔍 Analyzing reverb tail...")
    
    reverb = ReverbEffect(room_size=0.7, wet_level=0.8, dry_level=0.2)
    
    # Create short burst
    num_samples = 44100 * 3  # 3 seconds
    burst = np.zeros(num_samples)
    burst[1000:1100] = 0.5  # 100-sample burst
    
    # Process through reverb
    output = reverb.process(burst)
    
    # Analyze tail (after the burst)
    tail_start = 2000  # Well after the burst
    tail = output[tail_start:]
    
    # Check tail decay
    tail_rms_windows = []
    window_size = 4410  # 100ms windows
    
    for i in range(0, len(tail) - window_size, window_size):
        window = tail[i:i + window_size]
        rms = np.sqrt(np.mean(window**2))
        tail_rms_windows.append(rms)
    
    print(f"  Tail analysis over {len(tail_rms_windows)} windows:")
    
    # Check for proper decay
    if len(tail_rms_windows) >= 3:
        initial_rms = tail_rms_windows[0]
        mid_rms = tail_rms_windows[len(tail_rms_windows)//2]
        final_rms = tail_rms_windows[-1]
        
        print(f"    Initial RMS: {initial_rms:.6f}")
        print(f"    Mid RMS:     {mid_rms:.6f}")
        print(f"    Final RMS:   {final_rms:.6f}")
        
        # Check decay behavior
        if mid_rms > initial_rms:
            print("    ❌ Reverb tail grows instead of decaying")
        elif final_rms > mid_rms:
            print("    ❌ Reverb tail doesn't decay properly")
        elif final_rms < initial_rms * 0.01:  # Should decay to <1% of initial
            print("    ✅ Proper exponential decay")
        else:
            print("    ⚠️  Slow or incomplete decay")
    
    # Check for oscillations in tail
    tail_diff = np.abs(np.diff(tail[tail_start:tail_start+4410]))  # First 100ms of tail
    max_diff = np.max(tail_diff)
    mean_diff = np.mean(tail_diff)
    
    if max_diff > mean_diff * 10:  # Large spikes in tail
        print("    ❌ Oscillations or spikes detected in tail")
    else:
        print("    ✅ Smooth tail behavior")


def analyze_early_reflections():
    """Analyze early reflection behavior."""
    print("\n🔍 Analyzing early reflections...")
    
    reverb = ReverbEffect(room_size=0.5, wet_level=0.6, dry_level=0.4)
    
    # Sharp impulse
    impulse = np.zeros(8192)
    impulse[1000] = 1.0
    
    output = reverb.process(impulse)
    
    # Look at early reflections (first 50ms after impulse)
    early_window = output[1001:1001+2205]  # ~50ms at 44.1kHz
    
    # Find peaks (reflections)
    peaks = []
    threshold = 0.01  # Minimum peak height
    
    for i in range(1, len(early_window)-1):
        if (early_window[i] > early_window[i-1] and 
            early_window[i] > early_window[i+1] and 
            abs(early_window[i]) > threshold):
            peaks.append((i, early_window[i]))
    
    print(f"  Found {len(peaks)} early reflections above {threshold}")
    
    if len(peaks) == 0:
        print("    ❌ No early reflections - sounds will be unnatural")
    elif len(peaks) < 3:
        print("    ⚠️  Very few early reflections - may sound artificial")
    elif len(peaks) > 20:
        print("    ⚠️  Too many early reflections - may sound metallic")
    else:
        print("    ✅ Reasonable number of early reflections")
    
    # Show first few reflections
    for i, (pos, amp) in enumerate(peaks[:5]):
        time_ms = pos / 44.1  # Convert to milliseconds
        print(f"    Reflection {i+1}: {time_ms:.1f}ms, amplitude {amp:.4f}")


def analyze_metallic_artifacts():
    """Check for metallic/artificial artifacts."""
    print("\n🔍 Analyzing for metallic artifacts...")
    
    reverb = ReverbEffect(room_size=0.6, wet_level=0.7, dry_level=0.3)
    
    # Musical chord (more realistic test)
    sample_rate = 44100
    duration = 2.0
    num_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, num_samples, False)
    
    # C major chord: C4, E4, G4
    frequencies = [261.63, 329.63, 392.00]  # Hz
    chord = np.zeros(num_samples)
    
    for freq in frequencies:
        chord += 0.2 * np.sin(2 * np.pi * freq * t)
    
    # Apply envelope to make it more musical
    envelope = np.exp(-t * 2)  # Exponential decay
    chord *= envelope
    
    # Process through reverb
    reverb_chord = reverb.process(chord)
    
    # Analyze for artifacts
    # 1. Check for excessive high frequency content
    fft = np.fft.fft(reverb_chord)
    freqs = np.fft.fftfreq(len(fft), 1/sample_rate)
    magnitude = np.abs(fft)
    
    # Compare high freq content (>5kHz) to low freq content (<1kHz)
    high_freq_mask = (freqs > 5000) & (freqs < 20000)
    low_freq_mask = (freqs > 100) & (freqs < 1000)
    
    high_freq_energy = np.sum(magnitude[high_freq_mask])
    low_freq_energy = np.sum(magnitude[low_freq_mask])
    
    if high_freq_energy > low_freq_energy * 0.5:  # High freq >50% of low freq
        print("    ❌ Excessive high frequency content - may sound metallic")
    else:
        print("    ✅ Reasonable frequency balance")
    
    # 2. Check for periodic artifacts (comb filtering)
    autocorr = np.correlate(reverb_chord, reverb_chord, mode='full')
    autocorr = autocorr[autocorr.size // 2:]
    
    # Look for strong periodic components
    autocorr_normalized = autocorr / autocorr[0]
    strong_peaks = np.where(autocorr_normalized[100:] > 0.3)[0]  # Skip first 100 samples
    
    if len(strong_peaks) > 0:
        print(f"    ⚠️  Possible comb filtering detected at delays: {strong_peaks[:3] + 100}")
    else:
        print("    ✅ No obvious comb filtering artifacts")


def compare_with_dry_signal():
    """Compare reverb output with dry signal for sanity check."""
    print("\n🔍 Comparing with dry signal...")
    
    # Test with different wet/dry mixes
    test_configs = [
        {"wet_level": 0.0, "dry_level": 1.0, "name": "dry_only"},
        {"wet_level": 0.3, "dry_level": 0.7, "name": "subtle"},
        {"wet_level": 0.5, "dry_level": 0.5, "name": "balanced"},
        {"wet_level": 1.0, "dry_level": 0.0, "name": "wet_only"},
    ]
    
    # Test signal - simple sine wave
    sample_rate = 44100
    duration = 0.5
    num_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, num_samples, False)
    test_signal = 0.3 * np.sin(2 * np.pi * 440 * t)  # A4
    
    for config in test_configs:
        name = config.pop("name")
        reverb = ReverbEffect(room_size=0.5, **config)
        
        output = reverb.process(test_signal.copy())
        
        # Measure RMS levels
        input_rms = np.sqrt(np.mean(test_signal**2))
        output_rms = np.sqrt(np.mean(output**2))
        
        gain_db = 20 * np.log10(output_rms / input_rms) if input_rms > 0 else -100
        
        print(f"  {name:12s}: {gain_db:+6.2f} dB")
        
        # Sanity checks
        if name == "dry_only" and abs(gain_db) > 0.1:
            print(f"    ❌ Dry-only should have 0dB gain, got {gain_db:.2f}dB")
        elif name == "wet_only" and gain_db < -6:
            print(f"    ❌ Wet-only unusually quiet: {gain_db:.2f}dB")


def test_with_real_instrument():
    """Test reverb with actual instrument output."""
    print("\n🔍 Testing with real instrument...")
    
    # Create instrument with reverb
    instrument_data = {
        "name": "test_reverb_quality",
        "oscillators": [
            {"waveform": "sawtooth", "amplitude": 0.6},
            {"waveform": "sine", "amplitude": 0.4}
        ],
        "attack": 0.1, "decay": 0.2, "sustain_level": 0.7, "release": 0.5,
        "effects": [
            {"type": "reverb", "room_size": 0.6, "wet_level": 0.4, "dry_level": 0.6}
        ]
    }
    
    instrument = Instrument.from_dict(instrument_data)
    
    # Play a note
    instrument.note_on("C4", velocity=0.8)
    
    # Capture several buffers
    all_output = []
    for _ in range(50):  # ~1 second of audio
        buffer = instrument.process(1024)
        all_output.extend(buffer)
    
    output_array = np.array(all_output)
    
    # Analyze the result
    max_amplitude = np.max(np.abs(output_array))
    rms_level = np.sqrt(np.mean(output_array**2))
    
    print(f"  Max amplitude: {max_amplitude:.4f}")
    print(f"  RMS level:     {rms_level:.4f}")
    
    # Check for clipping
    if max_amplitude >= 0.99:
        print("    ❌ Output is clipping")
    elif max_amplitude < 0.01:
        print("    ❌ Output is too quiet")
    else:
        print("    ✅ Output level seems reasonable")
    
    # Check for DC offset
    dc_offset = np.mean(output_array)
    if abs(dc_offset) > 0.01:
        print(f"    ⚠️  DC offset detected: {dc_offset:.4f}")
    else:
        print("    ✅ No significant DC offset")


def main():
    """Run all sound quality tests."""
    print("🚀 Reverb Sound Quality Analysis")
    print("=" * 50)
    
    try:
        analyze_frequency_response()
        analyze_reverb_tail()
        analyze_early_reflections()
        analyze_metallic_artifacts()
        compare_with_dry_signal()
        test_with_real_instrument()
        
        print("\n📊 Sound Quality Analysis Complete")
        print("\n💡 If reverb still sounds strange, the issues might be:")
        print("   • Delay line lengths not musically tuned")
        print("   • Feedback coefficients too high/low")
        print("   • Missing diffusion/all-pass filters")
        print("   • Unrealistic room simulation")
        print("   • Need for modulation to reduce metallic sound")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
