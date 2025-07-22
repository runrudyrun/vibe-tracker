#!/usr/bin/env python3
"""
Debug script for testing the sequencer with detailed logging.
This script will help identify where the loop freezes.
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
        level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.FileHandler('sequencer_debug.log', mode='w'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=== SEQUENCER DEBUG SESSION STARTED ===")
    return logger

def create_test_composition():
    """Create a simple test composition for debugging."""
    logger = logging.getLogger(__name__)
    logger.info("Creating test composition...")
    
    # Create a simple instrument
    test_instrument = Instrument(
        name='debug_test',
        oscillators=[{'waveform': 'sine', 'amplitude': 0.5}], 
        attack=0.1, 
        decay=0.1, 
        sustain_level=0.7, 
        release=0.5
    )
    instruments = {'test_synth': test_instrument}
    logger.info(f"Created instrument: {test_instrument.name}")

    # Create a simple pattern with a few notes
    test_pattern = Pattern()
    test_pattern.steps = [None] * 16  # 16 steps
    
    # Add some notes
    test_pattern.steps[0] = NoteEvent(note='C4', velocity=0.8, duration=2)
    test_pattern.steps[4] = NoteEvent(note='E4', velocity=0.7, duration=2)
    test_pattern.steps[8] = NoteEvent(note='G4', velocity=0.6, duration=2)
    test_pattern.steps[12] = NoteEvent(note='C5', velocity=0.5, duration=2)
    
    logger.info(f"Created pattern with {len([s for s in test_pattern.steps if s])} notes")

    # Create track
    test_track = Track(instrument_id='test_synth', patterns=[test_pattern], sequence=[0])
    logger.info(f"Created track with instrument_id: {test_track.instrument_id}")

    # Create composition
    test_composition = Composition(bpm=120, tracks=[test_track])
    logger.info(f"Created composition with BPM: {test_composition.bpm}, tracks: {len(test_composition.tracks)}")
    
    return test_composition, instruments

def main():
    """Main debug function."""
    logger = setup_debug_logging()
    
    try:
        logger.info("Step 1: Creating test composition...")
        composition, instruments = create_test_composition()
        
        logger.info("Step 2: Creating sequencer...")
        sequencer = Sequencer(composition, instruments, logger=logger)
        
        logger.info("Step 3: Starting playback...")
        sequencer.play()
        
        logger.info("Step 4: Playing for 5 seconds...")
        for i in range(5):
            logger.info(f"Playback second {i+1}/5...")
            time.sleep(1)
            
            # Check if sequencer is still playing
            if not sequencer.is_playing:
                logger.error("SEQUENCER STOPPED UNEXPECTEDLY!")
                break
        
        logger.info("Step 5: Stopping sequencer...")
        sequencer.stop()
        
        logger.info("=== DEBUG SESSION COMPLETED SUCCESSFULLY ===")
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        if 'sequencer' in locals():
            sequencer.stop()
    except Exception as e:
        logger.error(f"CRITICAL ERROR: {e}", exc_info=True)
        if 'sequencer' in locals():
            sequencer.stop()
    
    logger.info("Debug script finished")

if __name__ == '__main__':
    main()
