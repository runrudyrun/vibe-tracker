#!/usr/bin/env python3
"""
Test script to verify TUI pattern save/load integration works correctly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tui import MusicEngine
from src.music_structures import Composition, Track, Pattern, NoteEvent
from src.synthesis import Instrument
import logging
import asyncio

def create_test_music_engine():
    """Create a MusicEngine with test data similar to what TUI would have."""
    # Create logger
    logger = logging.getLogger('test')
    logger.setLevel(logging.INFO)
    
    # Create music engine with TEST patterns directory
    engine = MusicEngine(logger)
    # Override pattern manager to use test directory
    engine.pattern_manager = engine.pattern_manager.__class__("test_patterns_integration")
    
    # Create a test composition with pattern and instrument
    composition = Composition(bpm=120)
    
    # Create a kick pattern
    pattern = Pattern(steps=[None] * 16)
    pattern.steps[0] = NoteEvent(note='C2', velocity=100, duration=1)
    pattern.steps[4] = NoteEvent(note='C2', velocity=80, duration=1)
    pattern.steps[8] = NoteEvent(note='C2', velocity=100, duration=1)
    pattern.steps[12] = NoteEvent(note='C2', velocity=90, duration=1)
    
    # Create track
    track = Track(instrument_id='test_kick')
    track.patterns = [pattern]
    track.sequence = [0]
    
    composition.tracks = [track]
    
    # Create instrument
    instrument = Instrument(
        name='test_kick',
        oscillators=[{'waveform': 'sine', 'amplitude': 0.8}],
        attack=0.01,
        decay=0.1,
        sustain_level=0.3,
        release=0.2
    )
    
    # Update engine state
    engine.composition = composition
    engine.instruments = {'test_kick': instrument}
    engine.sequencer.update_composition(composition, engine.instruments)
    
    return engine

def print_composition_state(engine, title):
    """Print the current state of the composition."""
    print(f"\n=== {title} ===")
    print(f"Tracks: {len(engine.composition.tracks)}")
    print(f"Instruments: {list(engine.instruments.keys())}")
    
    for i, track in enumerate(engine.composition.tracks):
        print(f"Track {i}: {track.instrument_id}")
        if track.patterns:
            pattern = track.patterns[0]
            active_steps = [(j, step.note, step.velocity) 
                          for j, step in enumerate(pattern.steps) 
                          if step and step.note]
            print(f"  Pattern steps: {len(pattern.steps)}")
            print(f"  Active notes: {active_steps}")
        else:
            print("  No patterns")

async def test_pattern_save_load_integration():
    """Test the complete pattern save/load cycle as it would work in TUI."""
    print("Testing TUI Pattern Save/Load Integration")
    print("=" * 50)
    
    # Create test music engine
    engine = create_test_music_engine()
    print_composition_state(engine, "ORIGINAL STATE")
    
    # Simulate saving a pattern (like worker_save_pattern would do)
    print("\n" + "="*50)
    print("SIMULATING PATTERN SAVE...")
    
    if not engine.composition.tracks:
        print("ERROR: No tracks to save from!")
        return
        
    track = engine.composition.tracks[0]
    if not track.patterns:
        print("ERROR: No patterns to save!")
        return
        
    pattern = track.patterns[0]
    instrument_id = track.instrument_id
    
    # Generate tags (same logic as in TUI)
    tags = []
    if instrument_id:
        tags.append(instrument_id.replace('_', ' '))
    
    active_steps = sum(1 for step in pattern.steps if step and step.note)
    if active_steps <= 4:
        tags.append("sparse")
    elif active_steps >= 12:
        tags.append("dense")
    else:
        tags.append("medium")
    
    # Save pattern
    success = engine.pattern_manager.save_pattern(
        pattern, "test_integration", tags=tags, instrument_id=instrument_id
    )
    
    print(f"Save success: {success}")
    if success:
        tags_str = ", ".join(tags) if tags else "no tags"
        print(f"Pattern saved with tags: {tags_str}")
    
    # Clear composition to simulate loading into empty state
    print("\n" + "="*50)
    print("CLEARING COMPOSITION...")
    engine.composition.tracks = []
    engine.instruments = {}
    engine.sequencer.update_composition(engine.composition, engine.instruments)
    print_composition_state(engine, "CLEARED STATE")
    
    # Simulate loading a pattern (like worker_load_pattern would do)
    print("\n" + "="*50)
    print("SIMULATING PATTERN LOAD...")
    
    result = engine.pattern_manager.load_pattern("test_integration")
    
    if not result:
        print("ERROR: Pattern not found!")
        return
        
    pattern, metadata = result
    instrument_id = metadata.get('instrument_id', 'default')
    
    print(f"Loaded metadata: {metadata}")
    
    # Create new track
    from src.music_structures import Track
    new_track = Track(instrument_id=instrument_id)
    new_track.patterns = [pattern]
    new_track.sequence = [0]
    
    # Ensure instrument exists (same logic as in TUI)
    if instrument_id not in engine.instruments:
        from src.synthesis import Instrument
        default_instrument = Instrument(
            name=instrument_id,
            oscillators=[{'waveform': 'sine', 'amplitude': 0.7}],
            attack=0.01,
            decay=0.1,
            sustain_level=0.7,
            release=0.2
        )
        engine.instruments[instrument_id] = default_instrument
        print(f"Created default instrument for '{instrument_id}'")
    
    # Add to composition
    engine.composition.tracks.append(new_track)
    
    # Update sequencer
    engine.sequencer.update_composition(engine.composition, engine.instruments)
    
    print("Pattern loaded successfully!")
    print_composition_state(engine, "LOADED STATE")
    
    # Compare original vs loaded
    print("\n" + "="*50)
    print("COMPARISON RESULTS:")
    
    if len(engine.composition.tracks) == 1:
        loaded_track = engine.composition.tracks[0]
        if loaded_track.patterns:
            loaded_pattern = loaded_track.patterns[0]
            
            # Compare active notes
            loaded_notes = [(j, step.note, step.velocity) 
                          for j, step in enumerate(loaded_pattern.steps) 
                          if step and step.note]
            expected_notes = [(0, 'C2', 100), (4, 'C2', 80), (8, 'C2', 100), (12, 'C2', 90)]
            
            print(f"Expected notes: {expected_notes}")
            print(f"Loaded notes: {loaded_notes}")
            print(f"Notes match: {loaded_notes == expected_notes}")
            
            print(f"Expected instrument: test_kick")
            print(f"Loaded instrument: {loaded_track.instrument_id}")
            print(f"Instrument match: {loaded_track.instrument_id == 'test_kick'}")
            
            print(f"Instrument exists in engine: {'test_kick' in engine.instruments}")
        else:
            print("ERROR: No patterns in loaded track!")
    else:
        print(f"ERROR: Expected 1 track, got {len(engine.composition.tracks)}")
    
    # Clean up TEST directory safely
    cleanup_success = engine.pattern_manager.safe_cleanup_test_directory()
    if cleanup_success:
        print("\nSafely cleaned up test files.")
    else:
        print("\nFailed to clean up test files.")

async def main():
    await test_pattern_save_load_integration()

if __name__ == "__main__":
    asyncio.run(main())
