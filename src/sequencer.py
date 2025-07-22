import time
import bisect
import threading
import numpy as np
import sounddevice as sd

from .music_structures import Composition
from .synthesis import SAMPLE_RATE


class Sequencer:
    """Plays a Composition object using a real-time, callback-based audio stream."""

    def __init__(self, composition: Composition, instruments: dict, logger=None):
        self._lock = threading.Lock()
        self.composition = composition
        self.instruments = instruments
        self.logger = logger

        self.is_playing = False
        self._stream = None
        self._current_frame = 0
        self._note_off_events = []  # List of (frame, (instrument, note_name)) tuples

    def update_composition(self, new_composition, new_instruments):
        """Thread-safely update the composition and instruments."""
        with self._lock:
            self.composition = new_composition
            self.instruments = new_instruments
            self._current_frame = 0
            self._note_off_events.clear()
            # Stop all notes on all instruments immediately to prevent stuck notes
            for instrument in self.instruments.values():
                instrument.active_notes.clear()

    def _audio_callback(self, outdata, frames, time, status):
        """The heart of the sequencer. Called by the audio driver to get samples."""
        with self._lock:
            start_frame = self._current_frame
            end_frame = start_frame + frames
            step_duration_frames = int(self.composition.get_step_duration() * SAMPLE_RATE)

            if step_duration_frames > 0:
                # --- 1. Schedule Note On/Off Events for the current block ---
                # Use a fixed loop length of 64 steps for consistent synchronization
                total_loop_steps = 64  # Standard pattern length

                start_step = start_frame // step_duration_frames
                end_step = end_frame // step_duration_frames

                # --- 1a. Trigger scheduled Note OFF events --- 
                processed_events = 0
                for i, (frame, (instrument, note_name)) in enumerate(self._note_off_events):
                    if frame < end_frame:
                        if frame >= start_frame:
                            # This event is within the current block
                            instrument.note_off(note_name)
                        processed_events = i + 1
                    else:
                        # Events are sorted, so we can stop here
                        break
                
                # --- 1b. Clean up processed Note OFF events ---
                if processed_events > 0:
                    self._note_off_events = self._note_off_events[processed_events:]

                # --- 1c. Trigger Note ON events for steps in this block ---
                for step in range(start_step, end_step + 1):
                    current_loop_step = step % total_loop_steps
                    for track in self.composition.tracks:
                        if not track.patterns or not track.sequence: continue
                        
                        # Use the first pattern and loop it properly
                        pattern_index = track.sequence[0] if track.sequence else 0
                        if pattern_index >= len(track.patterns): continue
                        
                        pattern = track.patterns[pattern_index]
                        if not pattern.steps: continue

                        # Each track loops its pattern independently within the global loop
                        pattern_step = current_loop_step % len(pattern.steps)
                        note_event = pattern.steps[pattern_step]

                        if note_event and note_event.note:
                            instrument = self.instruments.get(track.instrument_id)
                            if instrument:
                                # NOTE ON
                                instrument.note_on(note_event.note, note_event.velocity)
                                
                                # Schedule NOTE OFF
                                duration_in_frames = int(note_event.duration * step_duration_frames)
                                note_off_frame = (step * step_duration_frames) + duration_in_frames
                                
                                # Insert into sorted list to maintain order
                                event_tuple = (note_off_frame, (instrument, note_event.note))
                                bisect.insort(self._note_off_events, event_tuple)

            # --- 2. Mix audio from all instruments ---
            output_buffer = np.zeros((frames, 1), dtype=np.float32)
            for instrument in self.instruments.values():
                # Instrument processes its own active notes and returns mixed audio
                output_buffer += instrument.process(frames).reshape(-1, 1)

            # --- 3. Finalize and update state ---
            # Simple limiter to prevent clipping
            np.clip(output_buffer, -1.0, 1.0, out=output_buffer)
            
            outdata[:] = output_buffer
            self._current_frame = end_frame

    def play(self):
        """Starts the sequencer playback."""
        if self.is_playing:
            return
        if not self.composition.tracks:
            if self.logger:
                self.logger.warning("Attempted to play an empty composition. No tracks to play.")
            return

        self._current_frame = 0
        self._note_off_events.clear()
        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            callback=self._audio_callback,
            dtype='float32'
        )
        self._stream.start()
        self.is_playing = True

    def stop(self):
        """Stops the sequencer playback and closes the stream."""
        if not self.is_playing:
            return
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self.is_playing = False


if __name__ == '__main__':
    from .music_structures import Pattern, Track, Composition, NoteEvent
    from .synthesis import Instrument, sine_wave, triangle_wave

    print("Creating a test composition with a long drone note...")

    # 1. Instruments
    drone_instrument = Instrument(
        oscillators=[{'waveform': 'triangle', 'amplitude': 1.0}], 
        attack=0.5, 
        decay=0.5, 
        sustain_level=0.8, 
        release=2.0
    )
    instruments = {'drone': drone_instrument}

    # 2. Pattern with a long note
    drone_pattern = Pattern()
    # This note starts at step 0 and lasts for 64 steps (a full pattern)
    long_note = NoteEvent(note='C3', velocity=0.7, duration=64)
    drone_pattern.steps[0] = long_note

    # 3. Track
    drone_track = Track(instrument_id='drone', patterns=[drone_pattern], sequence=[0])

    # 4. Composition
    test_composition = Composition(bpm=60, tracks=[drone_track])

    # --- Play the composition ---
    sequencer = Sequencer(test_composition, instruments)
    
    try:
        sequencer.play()
        print("Playing a complex drone note for 10 seconds... Press Ctrl+C to stop.")
        time.sleep(10)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        sequencer.stop()
        print("Sequencer stopped.")

