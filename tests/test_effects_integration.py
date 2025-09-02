#!/usr/bin/env python3
"""
Test script for audio effects integration with LLM-driven workflow.

This test verifies:
1. Effects can be created from LLM JSON data
2. Instrument serialization/deserialization works with effects
3. Effects are properly applied during audio processing
4. LLM can generate compositions with effects
"""

import sys
import os
import numpy as np
import json

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from synthesis import Instrument
from effects import ReverbEffect, create_effect_from_dict
from llm_generator import LLMGenerator


def test_reverb_effect_creation():
    """Test creating reverb effect from dictionary."""
    print("🎵 Testing reverb effect creation...")
    
    # Test with default parameters
    reverb_data = {"type": "reverb"}
    reverb = create_effect_from_dict(reverb_data)
    
    assert reverb.effect_type == "reverb"
    assert reverb.enabled == True
    assert reverb.get_param('room_size') == 0.5  # default
    
    # Test with custom parameters
    custom_reverb_data = {
        "type": "reverb",
        "room_size": 0.7,
        "wet_level": 0.4,
        "dry_level": 0.6,
        "enabled": True
    }
    custom_reverb = create_effect_from_dict(custom_reverb_data)
    
    assert custom_reverb.get_param('room_size') == 0.7
    assert custom_reverb.get_param('wet_level') == 0.4
    assert custom_reverb.get_param('dry_level') == 0.6
    
    print("✅ Reverb effect creation works!")


def test_reverb_audio_processing():
    """Test that reverb actually processes audio."""
    print("🎵 Testing reverb audio processing...")
    
    # Create reverb with noticeable settings
    reverb = ReverbEffect(room_size=0.8, wet_level=0.5, dry_level=0.5)
    
    # Generate test audio (simple sine wave)
    sample_rate = 44100
    duration = 0.1  # 100ms
    num_samples = int(sample_rate * duration)
    frequency = 440  # A4
    
    t = np.linspace(0, duration, num_samples, False)
    test_audio = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    # Process through reverb
    processed_audio = reverb.process(test_audio)
    
    # Verify output is different from input
    assert not np.array_equal(test_audio, processed_audio)
    assert len(processed_audio) == len(test_audio)
    
    # Verify output is not silent
    assert np.max(np.abs(processed_audio)) > 0.01
    
    print("✅ Reverb audio processing works!")


def test_instrument_effects_serialization():
    """Test instrument serialization with effects."""
    print("🎵 Testing instrument effects serialization...")
    
    # Create instrument with effects via JSON (LLM-style)
    instrument_data = {
        "name": "test_synth",
        "oscillators": [{"waveform": "sawtooth", "amplitude": 0.8}],
        "attack": 0.02,
        "decay": 0.1,
        "sustain_level": 0.6,
        "release": 0.3,
        "effects": [
            {
                "type": "reverb",
                "room_size": 0.6,
                "wet_level": 0.3,
                "dry_level": 0.7
            }
        ]
    }
    
    # Create instrument from dict (simulates LLM workflow)
    instrument = Instrument.from_dict(instrument_data)
    
    # Verify effects were created
    assert len(instrument.effects) == 1
    assert instrument.effects[0].effect_type == "reverb"
    assert instrument.effects[0].get_param('room_size') == 0.6
    
    # Test serialization back to dict
    serialized = instrument.to_dict()
    assert 'effects' in serialized
    assert len(serialized['effects']) == 1
    assert serialized['effects'][0]['type'] == "reverb"
    assert serialized['effects'][0]['room_size'] == 0.6
    
    # Test round-trip serialization
    instrument2 = Instrument.from_dict(serialized)
    assert len(instrument2.effects) == 1
    assert instrument2.effects[0].get_param('room_size') == 0.6
    
    print("✅ Instrument effects serialization works!")


def test_instrument_audio_with_effects():
    """Test that instrument applies effects during audio processing."""
    print("🎵 Testing instrument audio processing with effects...")
    
    # Create two identical instruments, one with reverb, one without
    base_data = {
        "name": "test",
        "oscillators": [{"waveform": "sine", "amplitude": 1.0}],
        "attack": 0.01,
        "decay": 0.1,
        "sustain_level": 0.7,
        "release": 0.2
    }
    
    instrument_no_fx = Instrument.from_dict(base_data)
    
    reverb_data = base_data.copy()
    reverb_data["effects"] = [{"type": "reverb", "wet_level": 0.5}]
    instrument_with_fx = Instrument.from_dict(reverb_data)
    
    # Trigger same note on both
    instrument_no_fx.note_on("C4", velocity=0.8)
    instrument_with_fx.note_on("C4", velocity=0.8)
    
    # Process audio
    num_samples = 1024
    audio_no_fx = instrument_no_fx.process(num_samples)
    audio_with_fx = instrument_with_fx.process(num_samples)
    
    # Verify they produce different output
    assert not np.array_equal(audio_no_fx, audio_with_fx)
    
    # Both should produce sound
    assert np.max(np.abs(audio_no_fx)) > 0.01
    assert np.max(np.abs(audio_with_fx)) > 0.01
    
    print("✅ Instrument audio processing with effects works!")


def test_llm_effects_integration():
    """Test that LLM can generate compositions with effects."""
    print("🎵 Testing LLM effects integration...")
    
    # Create a mock composition with effects (simulates LLM output)
    llm_composition = {
        "bpm": 120,
        "instruments": [
            {
                "name": "reverb_pad",
                "oscillators": [
                    {"waveform": "sawtooth", "amplitude": 0.6},
                    {"waveform": "sine", "amplitude": 0.4}
                ],
                "attack": 0.5,
                "decay": 0.3,
                "sustain_level": 0.8,
                "release": 1.0,
                "effects": [
                    {
                        "type": "reverb",
                        "room_size": 0.7,
                        "damping": 0.4,
                        "wet_level": 0.4,
                        "dry_level": 0.6
                    }
                ]
            }
        ],
        "tracks": [
            {
                "instrument_name": "reverb_pad",
                "notes": [
                    {"step": 0, "note": "C3", "duration": 16},
                    {"step": 16, "note": "F3", "duration": 16},
                    {"step": 32, "note": "G3", "duration": 16},
                    {"step": 48, "note": "C4", "duration": 16}
                ]
            }
        ]
    }
    
    # Verify we can create instruments from this data
    instrument_data = llm_composition["instruments"][0]
    instrument = Instrument.from_dict(instrument_data)
    
    # Verify effects were properly loaded
    assert len(instrument.effects) == 1
    reverb = instrument.effects[0]
    assert reverb.effect_type == "reverb"
    assert reverb.get_param('room_size') == 0.7
    assert reverb.get_param('damping') == 0.4
    
    # Test that it can process audio
    instrument.note_on("C3", velocity=0.7)
    audio = instrument.process(2048)
    assert np.max(np.abs(audio)) > 0.01
    
    print("✅ LLM effects integration works!")


def test_effects_performance():
    """Test that effects don't cause significant performance degradation."""
    print("🎵 Testing effects performance...")
    
    import time
    
    # Create instrument with multiple effects
    instrument_data = {
        "name": "fx_test",
        "oscillators": [{"waveform": "sawtooth", "amplitude": 1.0}],
        "attack": 0.01,
        "decay": 0.1,
        "sustain_level": 0.7,
        "release": 0.2,
        "effects": [
            {"type": "reverb", "room_size": 0.5, "wet_level": 0.3}
        ]
    }
    
    instrument = Instrument.from_dict(instrument_data)
    instrument.note_on("C4", velocity=0.8)
    
    # Time processing of realistic audio buffer size
    num_samples = 1024  # ~23ms at 44.1kHz
    num_iterations = 100
    
    start_time = time.time()
    for _ in range(num_iterations):
        audio = instrument.process(num_samples)
    end_time = time.time()
    
    avg_time_ms = ((end_time - start_time) / num_iterations) * 1000
    
    print(f"   Average processing time: {avg_time_ms:.3f}ms per buffer")
    
    # Should be well under real-time (23ms for 1024 samples at 44.1kHz)
    assert avg_time_ms < 10.0, f"Effects processing too slow: {avg_time_ms}ms"
    
    print("✅ Effects performance is acceptable!")


def main():
    """Run all effects integration tests."""
    print("🚀 Starting Effects Integration Tests\n")
    
    try:
        test_reverb_effect_creation()
        test_reverb_audio_processing()
        test_instrument_effects_serialization()
        test_instrument_audio_with_effects()
        test_llm_effects_integration()
        test_effects_performance()
        
        print("\n🎉 ALL EFFECTS TESTS PASSED!")
        print("\n📋 Summary:")
        print("   ✅ Reverb effect creation and configuration")
        print("   ✅ Audio processing with reverb")
        print("   ✅ Instrument serialization with effects")
        print("   ✅ Effects integration in audio pipeline")
        print("   ✅ LLM-compatible effects workflow")
        print("   ✅ Performance within acceptable limits")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
