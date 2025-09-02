#!/usr/bin/env python3
"""
Test LLM-driven ambient pad generation with reverb.

This simulates the complete workflow:
1. LLM generates ambient pad with reverb
2. Test real-time playback (check for dropouts)
3. Test WAV export (check for overload)
4. Analyze audio quality and performance
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
# Skip sequencer import for now - not needed for this test
# from sequencer import Sequencer
# from music_structures import Composition, Track, Pattern, NoteEvent


def test_llm_ambient_generation():
    """Test LLM generation of ambient pad with reverb."""
    print("🎵 Testing LLM ambient pad generation with reverb...")
    
    try:
        generator = LLMGenerator()
        
        # Request ambient pad with reverb
        prompt = "Create a dreamy ambient pad with lush reverb, slow attack, and sustained notes"
        
        print(f"Sending prompt: '{prompt}'")
        composition_data, error = generator.generate_music_from_prompt(prompt)
        
        if error:
            print(f"❌ LLM Error: {error}")
            return None
        
        if not composition_data:
            print("❌ No composition generated")
            return None
        
        print("✅ LLM generated composition successfully")
        
        # Analyze what was generated
        instruments = composition_data.get('instruments', [])
        tracks = composition_data.get('tracks', [])
        
        print(f"Generated {len(instruments)} instruments, {len(tracks)} tracks")
        
        # Look for reverb effects
        reverb_instruments = []
        for instrument_data in instruments:
            effects = instrument_data.get('effects', [])
            reverb_effects = [e for e in effects if e.get('type') == 'reverb']
            if reverb_effects:
                reverb_instruments.append({
                    'name': instrument_data.get('name'),
                    'reverb': reverb_effects[0],
                    'data': instrument_data
                })
        
        if reverb_instruments:
            print(f"✅ Found {len(reverb_instruments)} instruments with reverb:")
            for inst in reverb_instruments:
                reverb = inst['reverb']
                print(f"  • {inst['name']}: room_size={reverb.get('room_size', 0.5)}, wet_level={reverb.get('wet_level', 0.3)}")
        else:
            print("⚠️  No reverb effects found in generated composition")
        
        return composition_data, reverb_instruments
        
    except Exception as e:
        print(f"❌ LLM generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_instrument_creation_and_playback(reverb_instruments):
    """Test creating instruments and checking for audio issues."""
    print("\n🔧 Testing instrument creation and playback...")
    
    issues = []
    
    for inst_info in reverb_instruments:
        name = inst_info['name']
        instrument_data = inst_info['data']
        
        print(f"Testing instrument: {name}")
        
        try:
            # Create instrument
            instrument = Instrument.from_dict(instrument_data)
            print(f"  ✅ Created instrument with {len(instrument.effects)} effect(s)")
            
            # Test note triggering and processing
            instrument.note_on("C3", velocity=0.7)
            
            # Process multiple buffers to simulate real playback
            total_samples = 0
            max_amplitude = 0
            processing_times = []
            
            for i in range(100):  # ~2.3 seconds of audio
                start_time = time.perf_counter()
                
                buffer = instrument.process(1024)
                
                end_time = time.perf_counter()
                processing_times.append((end_time - start_time) * 1000)  # ms
                
                total_samples += len(buffer)
                current_max = np.max(np.abs(buffer))
                max_amplitude = max(max_amplitude, current_max)
                
                # Check for dropouts (silence when there should be sound)
                if i > 10 and current_max < 0.001:  # After attack phase
                    issues.append(f"{name}: Possible dropout at buffer {i}")
                
                # Check for clipping
                if current_max >= 0.99:
                    issues.append(f"{name}: Clipping detected (amplitude: {current_max:.3f})")
            
            # Analyze processing performance
            avg_time = np.mean(processing_times)
            max_time = np.max(processing_times)
            
            print(f"  📊 Performance: avg={avg_time:.2f}ms, max={max_time:.2f}ms")
            print(f"  📊 Max amplitude: {max_amplitude:.3f}")
            
            # Check for performance issues
            if avg_time > 20:  # 20ms is roughly real-time limit for 1024 samples
                issues.append(f"{name}: Slow processing (avg: {avg_time:.2f}ms)")
            
            if max_time > 50:  # Occasional very slow processing
                issues.append(f"{name}: Occasional slow processing (max: {max_time:.2f}ms)")
            
            # Check amplitude levels
            if max_amplitude > 0.95:
                issues.append(f"{name}: High amplitude risk ({max_amplitude:.3f})")
            elif max_amplitude < 0.01:
                issues.append(f"{name}: Very quiet output ({max_amplitude:.3f})")
            
        except Exception as e:
            issues.append(f"{name}: Exception during processing: {e}")
            print(f"  ❌ Error: {e}")
    
    return issues


def test_wav_export_simulation(reverb_instruments):
    """Simulate WAV export to check for overload issues."""
    print("\n💾 Testing WAV export simulation...")
    
    if not reverb_instruments:
        print("⚠️  No reverb instruments to test")
        return []
    
    issues = []
    
    # Take the first reverb instrument for testing
    inst_info = reverb_instruments[0]
    name = inst_info['name']
    instrument_data = inst_info['data']
    
    print(f"Simulating WAV export with instrument: {name}")
    
    try:
        instrument = Instrument.from_dict(instrument_data)
        
        # Simulate a longer composition (like WAV export would do)
        sample_rate = 44100
        duration = 10.0  # 10 seconds
        total_samples = int(sample_rate * duration)
        
        # Trigger multiple notes (polyphony test)
        notes = ["C3", "E3", "G3", "C4"]
        for i, note in enumerate(notes):
            instrument.note_on(note, velocity=0.6)
        
        # Generate audio in chunks (like real export)
        chunk_size = 4096
        all_audio = []
        max_chunk_amplitude = 0
        
        print("  Generating audio chunks...")
        for chunk_start in range(0, total_samples, chunk_size):
            chunk_samples = min(chunk_size, total_samples - chunk_start)
            
            chunk = instrument.process(chunk_samples)
            all_audio.extend(chunk)
            
            chunk_max = np.max(np.abs(chunk))
            max_chunk_amplitude = max(max_chunk_amplitude, chunk_max)
            
            # Progress indicator
            if chunk_start % (sample_rate * 2) == 0:  # Every 2 seconds
                progress = chunk_start / total_samples * 100
                print(f"    Progress: {progress:.1f}%, max amplitude so far: {chunk_max:.3f}")
        
        # Analyze the complete audio
        audio_array = np.array(all_audio)
        
        # Check for overload issues
        clipped_samples = np.sum(np.abs(audio_array) >= 0.99)
        clipped_percentage = (clipped_samples / len(audio_array)) * 100
        
        rms_level = np.sqrt(np.mean(audio_array**2))
        peak_level = np.max(np.abs(audio_array))
        
        print(f"  📊 Export analysis:")
        print(f"    Duration: {len(audio_array) / sample_rate:.1f}s")
        print(f"    Peak level: {peak_level:.3f}")
        print(f"    RMS level: {rms_level:.3f}")
        print(f"    Clipped samples: {clipped_samples} ({clipped_percentage:.2f}%)")
        
        # Check for issues
        if peak_level >= 0.99:
            issues.append(f"WAV Export: Peak level too high ({peak_level:.3f})")
        
        if clipped_percentage > 0.1:  # More than 0.1% clipped
            issues.append(f"WAV Export: Excessive clipping ({clipped_percentage:.2f}%)")
        
        if rms_level > 0.5:  # Very hot signal
            issues.append(f"WAV Export: Very hot RMS level ({rms_level:.3f})")
        
        # Save a small sample for manual inspection
        if len(audio_array) > 0:
            sample_file = "reverb_test_sample.wav"
            try:
                # Save first 3 seconds as sample
                sample_length = min(len(audio_array), sample_rate * 3)
                sample_audio = audio_array[:sample_length]
                
                # Normalize to prevent clipping in file
                if np.max(np.abs(sample_audio)) > 0:
                    sample_audio = sample_audio / np.max(np.abs(sample_audio)) * 0.8
                
                # Convert to 16-bit
                sample_audio_16 = (sample_audio * 32767).astype(np.int16)
                
                with wave.open(sample_file, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(sample_audio_16.tobytes())
                
                print(f"  💾 Saved audio sample: {sample_file}")
                
            except Exception as e:
                print(f"  ⚠️  Could not save audio sample: {e}")
        
    except Exception as e:
        issues.append(f"WAV Export: Exception during generation: {e}")
        print(f"  ❌ Error: {e}")
    
    return issues


def main():
    """Run complete LLM ambient reverb test."""
    print("🚀 LLM Ambient Reverb Test Suite")
    print("=" * 50)
    
    # Step 1: Generate composition with LLM
    result = test_llm_ambient_generation()
    if not result:
        print("❌ Cannot proceed without LLM-generated composition")
        return False
    
    composition_data, reverb_instruments = result
    
    if not reverb_instruments:
        print("❌ No reverb instruments found - cannot test reverb issues")
        return False
    
    # Step 2: Test instrument creation and playback
    playback_issues = test_instrument_creation_and_playback(reverb_instruments)
    
    # Step 3: Test WAV export simulation
    export_issues = test_wav_export_simulation(reverb_instruments)
    
    # Summary
    all_issues = playback_issues + export_issues
    
    print("\n📊 Test Results Summary")
    print("=" * 30)
    
    if not all_issues:
        print("🎉 No issues detected!")
        print("   Reverb appears to work correctly in LLM workflow")
    else:
        print(f"⚠️  Found {len(all_issues)} issues:")
        for i, issue in enumerate(all_issues, 1):
            print(f"   {i}. {issue}")
        
        print("\n💡 Recommended fixes:")
        
        # Analyze issue patterns
        if any("Clipping" in issue or "High amplitude" in issue for issue in all_issues):
            print("   • Reduce reverb feedback or overall gain")
            print("   • Add better limiting/compression")
        
        if any("Slow processing" in issue for issue in all_issues):
            print("   • Optimize reverb algorithm for real-time performance")
            print("   • Consider reducing reverb complexity")
        
        if any("dropout" in issue.lower() for issue in all_issues):
            print("   • Check for buffer underruns in audio callback")
            print("   • Investigate note lifecycle with reverb")
    
    print(f"\n🎵 Generated composition summary:")
    print(f"   BPM: {composition_data.get('bpm', 'unknown')}")
    print(f"   Instruments: {len(composition_data.get('instruments', []))}")
    print(f"   Tracks: {len(composition_data.get('tracks', []))}")
    print(f"   Reverb instruments: {len(reverb_instruments)}")
    
    return len(all_issues) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
