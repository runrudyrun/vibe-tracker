#!/usr/bin/env python3
"""
Test script to debug pattern save/load functionality.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.music_structures import Composition, Track, Pattern, NoteEvent
from src.synthesis import Instrument
from src.pattern_manager import PatternManager
import json

def create_test_composition():
    """Create a test composition with a simple pattern."""
    composition = Composition(bpm=120)
    
    # Create a simple kick pattern
    pattern = Pattern(steps=[None] * 16)
    pattern.steps[0] = NoteEvent(note='C2', velocity=100, duration=1)  # Kick on step 1
    pattern.steps[4] = NoteEvent(note='C2', velocity=80, duration=1)   # Kick on step 5
    pattern.steps[8] = NoteEvent(note='C2', velocity=100, duration=1)  # Kick on step 9
    pattern.steps[12] = NoteEvent(note='C2', velocity=90, duration=1)  # Kick on step 13
    
    # Create track with the pattern
    track = Track(instrument_id='kick_drum')
    track.patterns = [pattern]
    track.sequence = [0]
    
    composition.tracks = [track]
    
    # Create instrument
    instrument = Instrument(
        name='kick_drum',
        oscillators=[{'waveform': 'sine', 'amplitude': 0.8}],
        attack=0.01,
        decay=0.1,
        sustain_level=0.3,
        release=0.2
    )
    
    return composition, {'kick_drum': instrument}

def print_pattern_details(pattern, title):
    """Print detailed pattern information."""
    print(f"\n=== {title} ===")
    print(f"Pattern steps: {len(pattern.steps)}")
    active_steps = []
    for i, step in enumerate(pattern.steps):
        if step and step.note:
            active_steps.append(f"Step {i}: {step.note} (vel={step.velocity}, dur={step.duration})")
    
    if active_steps:
        print("Active steps:")
        for step_info in active_steps:
            print(f"  {step_info}")
    else:
        print("No active steps found!")
    
    print(f"Pattern dict: {json.dumps(pattern.to_dict(), indent=2)}")

def main():
    print("Testing Pattern Save/Load Functionality")
    print("=" * 50)
    
    # Create test data
    composition, instruments = create_test_composition()
    original_pattern = composition.tracks[0].patterns[0]
    original_instrument_id = composition.tracks[0].instrument_id
    
    print(f"Original instrument_id: {original_instrument_id}")
    print_pattern_details(original_pattern, "ORIGINAL PATTERN")
    
    # Test pattern manager
    pm = PatternManager("test_patterns")
    
    # Save pattern
    print("\n" + "="*50)
    print("SAVING PATTERN...")
    success = pm.save_pattern(
        original_pattern, 
        "test_kick", 
        tags=["kick", "test"], 
        instrument_id=original_instrument_id
    )
    print(f"Save success: {success}")
    
    # Load pattern
    print("\n" + "="*50)
    print("LOADING PATTERN...")
    result = pm.load_pattern("test_kick")
    
    if result:
        loaded_pattern, metadata = result
        print(f"Load success: True")
        print(f"Metadata: {metadata}")
        print_pattern_details(loaded_pattern, "LOADED PATTERN")
        
        # Compare patterns
        print("\n" + "="*50)
        print("COMPARISON:")
        
        # Check steps count
        orig_steps = len(original_pattern.steps)
        load_steps = len(loaded_pattern.steps)
        print(f"Steps count - Original: {orig_steps}, Loaded: {load_steps}, Match: {orig_steps == load_steps}")
        
        # Check active notes
        orig_notes = [(i, step.note, step.velocity, step.duration) 
                     for i, step in enumerate(original_pattern.steps) 
                     if step and step.note]
        load_notes = [(i, step.note, step.velocity, step.duration) 
                     for i, step in enumerate(loaded_pattern.steps) 
                     if step and step.note]
        
        print(f"Original notes: {orig_notes}")
        print(f"Loaded notes: {load_notes}")
        print(f"Notes match: {orig_notes == load_notes}")
        
        # Check instrument_id
        orig_inst = original_instrument_id
        load_inst = metadata.get('instrument_id')
        print(f"Instrument ID - Original: {orig_inst}, Loaded: {load_inst}, Match: {orig_inst == load_inst}")
        
    else:
        print("Load failed!")
    
    # Clean up test files safely
    cleanup_success = pm.safe_cleanup_test_directory()
    if cleanup_success:
        print("\nSafely cleaned up test files.")
    else:
        print("\nFailed to clean up test files.")

if __name__ == "__main__":
    main()
