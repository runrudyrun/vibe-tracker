import time
import threading
import numpy as np
import sounddevice as sd

from src.music_structures import Composition, Pattern, Track
from src.synthesis import Instrument, SAMPLE_RATE, sine_wave

class Sequencer:
    """Plays a Composition object in real-time."""

    def __init__(self, composition: Composition, instruments: dict):
        self.composition = composition
        self.instruments = instruments
        self.is_playing = False
        self._playback_thread = None

    def _play_note_async(self, audio_data):
        """Plays audio data in a non-blocking way."""
        def play():
            sd.play(audio_data.astype(np.float32), SAMPLE_RATE)
            sd.wait()
        # Run playback in a separate thread to avoid blocking the main loop
        thread = threading.Thread(target=play)
        thread.start()

    def _sequencer_loop(self):
        """The main loop that iterates through the composition."""
        step_duration = self.composition.get_step_duration_seconds()
        current_step = 0

        while self.is_playing:
            loop_start_time = time.time()

            for track in self.composition.tracks:
                # For now, we assume a simple loop of the first pattern
                if not track.patterns:
                    continue
                
                pattern = track.patterns[0] # Simple case: play first pattern
                note_event = pattern.steps[current_step]

                if note_event:
                    instrument = self.instruments.get(track.instrument_id)
                    if instrument:
                        # Generate audio for one step duration
                        audio_data = instrument.play_note(
                            note_event.note_number,
                            step_duration
                        )
                        # Apply note volume
                        audio_data *= note_event.volume
                        self._play_note_async(audio_data)

            # Move to the next step
            current_step = (current_step + 1) % len(pattern.steps)

            # Wait for the correct amount of time to maintain BPM
            processing_time = time.time() - loop_start_time
            time_to_wait = max(0, step_duration - processing_time)
            time.sleep(time_to_wait)

    def play(self):
        """Starts the sequencer playback."""
        if not self.is_playing:
            self.is_playing = True
            self._playback_thread = threading.Thread(target=self._sequencer_loop)
            self._playback_thread.start()
            print("Sequencer started.")

    def stop(self):
        """Stops the sequencer playback."""
        if self.is_playing:
            self.is_playing = False
            if self._playback_thread:
                self._playback_thread.join() # Wait for the thread to finish
            print("Sequencer stopped.")


if __name__ == '__main__':
    # --- Create a test composition ---
    print("Creating a test composition...")
    
    # 1. Instruments
    # A simple sine wave for a kick drum sound (low frequency)
    kick_instrument = Instrument(waveform_func=sine_wave, attack=0.01, decay=0.15, sustain_level=0, release=0.1)
    instruments = {0: kick_instrument}

    # 2. Pattern
    # A classic 4/4 kick drum pattern
    kick_pattern = Pattern()
    kick_note = 36 # C2, a common kick drum note
    kick_pattern.set_note(0, kick_note)
    kick_pattern.set_note(16, kick_note)
    kick_pattern.set_note(32, kick_note)
    kick_pattern.set_note(48, kick_note)

    # 3. Track
    kick_track = Track(instrument_id=0, patterns=[kick_pattern])

    # 4. Composition
    test_composition = Composition(bpm=120, tracks=[kick_track])

    # --- Play the composition ---
    sequencer = Sequencer(test_composition, instruments)
    
    try:
        sequencer.play()
        print("Playing for 10 seconds... Press Ctrl+C to stop.")
        time.sleep(10)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        sequencer.stop()

