#!/usr/bin/env python3
"""
Debug script for testing multi-track sequencer performance.
This will help identify where the freeze occurs with multiple tracks.
"""

import sys
import os
import time
import logging

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.music_structures import Pattern, Track, Composition, NoteEvent
from src.synthesis import Instrument
from src.sequencer import Sequencer

def setup_debug_logging():
    """Setup detailed debug logging."""
    logging.basicConfig(
        level=logging.INFO,  # Use INFO to reduce log spam
        format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.FileHandler('multitrack_debug.log', mode='w'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=== MULTI-TRACK DEBUG SESSION STARTED ===")
    return logger

def create_test_track(track_id, instrument_name, base_note, pattern_length=16):
    """Create a test track with specified parameters."""
    logger = logging.getLogger(__name__)
    
    # Create instrument with simple sine wave to reduce CPU load
    instrument = Instrument(
        name=instrument_name,
        oscillators=[{'waveform': 'sine', 'amplitude': 0.3}],  # Lower amplitude
        attack=0.05, 
        decay=0.1, 
        sustain_level=0.6, 
        release=0.3
    )
    
    # Create pattern
    pattern = Pattern()
    pattern.steps = [None] * pattern_length
    
    # Add notes every 4 steps to avoid too much overlap
    notes = [base_note, f"{base_note[0]}#{base_note[1]}", f"{chr(ord(base_note[0])+1)}{base_note[1]}"]
    for i in range(0, pattern_length, 4):
        if i < len(notes) * 4:
            note_idx = i // 4
            if note_idx < len(notes):
                pattern.steps[i] = NoteEvent(
                    note=notes[note_idx], 
                    velocity=0.5,  # Lower velocity
                    duration=2     # Shorter duration
                )
    
    # Create track
    track = Track(instrument_id=instrument_name, patterns=[pattern], sequence=[0])
    
    logger.info(f"Created track {track_id}: {instrument_name} with base note {base_note}")
    return track, {instrument_name: instrument}

def test_multitrack_performance(num_tracks):
    """Test sequencer with specified number of tracks."""
    logger = setup_debug_logging()
    
    try:
        logger.info(f"=== TESTING {num_tracks} TRACKS ===")
        
        # Create multiple tracks
        all_tracks = []
        all_instruments = {}
        
        base_notes = ['C4', 'E4', 'G4', 'C5', 'E5', 'G5', 'C3', 'E3']
        
        for i in range(num_tracks):
            base_note = base_notes[i % len(base_notes)]
            instrument_name = f'synth_{i+1}'
            
            track, instruments = create_test_track(i+1, instrument_name, base_note)
            all_tracks.append(track)
            all_instruments.update(instruments)
        
        logger.info(f"Created {len(all_tracks)} tracks with {len(all_instruments)} instruments")
        
        # Create composition
        composition = Composition(bpm=120, tracks=all_tracks)
        logger.info(f"Created composition with BPM: {composition.bpm}")
        
        # Create sequencer
        logger.info("Creating sequencer...")
        sequencer = Sequencer(composition, all_instruments, logger=logger)
        
        # Start playback
        logger.info("Starting playback...")
        start_time = time.time()
        sequencer.play()
        
        # Monitor for 10 seconds
        for second in range(10):
            time.sleep(1)
            elapsed = time.time() - start_time
            
            if not sequencer.is_playing:
                logger.error(f"SEQUENCER STOPPED at {elapsed:.1f}s!")
                break
                
            # Check active notes count across all instruments
            total_active_notes = sum(len(inst.active_notes) for inst in all_instruments.values())
            logger.info(f"Second {second+1}: Still playing, total active notes: {total_active_notes}")
            
            if total_active_notes > 50:  # Warning threshold
                logger.warning(f"High note count detected: {total_active_notes}")
        
        logger.info("Stopping sequencer...")
        sequencer.stop()
        
        total_time = time.time() - start_time
        logger.info(f"=== TEST COMPLETED: {num_tracks} tracks ran for {total_time:.1f}s ===")
        
        return True
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR with {num_tracks} tracks: {e}", exc_info=True)
        if 'sequencer' in locals():
            sequencer.stop()
        return False

def main():
    """Main function to test different track counts."""
    logger = logging.getLogger(__name__)
    
    # Test with increasing number of tracks
    for num_tracks in [1, 2, 3, 4, 5]:
        logger.info(f"\n{'='*50}")
        logger.info(f"TESTING {num_tracks} TRACKS")
        logger.info(f"{'='*50}")
        
        success = test_multitrack_performance(num_tracks)
        
        if not success:
            logger.error(f"FAILED at {num_tracks} tracks!")
            break
        
        logger.info(f"SUCCESS with {num_tracks} tracks")
        
        # Small pause between tests
        time.sleep(2)
    
    logger.info("=== MULTI-TRACK DEBUG SESSION COMPLETED ===")

if __name__ == '__main__':
    main()
