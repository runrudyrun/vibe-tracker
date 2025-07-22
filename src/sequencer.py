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
        self._note_off_events = []  # List of (frame, event_id, (instrument, note_name)) tuples
        self._event_counter = 0  # Counter for unique event IDs

    def update_composition(self, new_composition, new_instruments):
        """Thread-safely update the composition and instruments."""
        with self._lock:
            self.composition = new_composition
            self.instruments = new_instruments
            self._current_frame = 0
            self._note_off_events.clear()
            self._event_counter = 0
            # Stop all notes on all instruments immediately to prevent stuck notes
            for instrument in self.instruments.values():
                instrument.active_notes.clear()

    def _audio_callback(self, outdata, frames, time, status):
        """The heart of the sequencer. Called by the audio driver to get samples."""
        if self.logger:
            self.logger.debug(f"[AUDIO_CALLBACK] Starting callback - frames: {frames}")
        
        with self._lock:
            if self.logger:
                self.logger.debug(f"[AUDIO_CALLBACK] Lock acquired")
            
            start_frame = self._current_frame
            end_frame = start_frame + frames
            step_duration_frames = int(self.composition.get_step_duration() * SAMPLE_RATE)

            if self.logger:
                self.logger.debug(f"[AUDIO_CALLBACK] step_duration_frames: {step_duration_frames}, start_frame: {start_frame}, end_frame: {end_frame}")

            if step_duration_frames > 0:
                if self.logger:
                    self.logger.debug(f"[AUDIO_CALLBACK] Processing steps...")
                
                # --- 1. Schedule Note On/Off Events for the current block ---
                all_pattern_lengths = [len(p.steps) for t in self.composition.tracks for p in t.patterns if p.steps]
                total_loop_steps = max(all_pattern_lengths) if all_pattern_lengths else 64

                start_step = start_frame // step_duration_frames
                end_step = end_frame // step_duration_frames

                if self.logger:
                    self.logger.debug(f"[AUDIO_CALLBACK] total_loop_steps: {total_loop_steps}, start_step: {start_step}, end_step: {end_step}")

                # --- 1a. Trigger scheduled Note OFF events --- 
                processed_events = 0
                for i, (frame, event_id, (instrument, note_name)) in enumerate(self._note_off_events):
                    if frame < end_frame:
                        if frame >= start_frame:
                            # This event is within the current block
                            if self.logger:
                                self.logger.debug(f"[AUDIO_CALLBACK] Note OFF: {note_name} at frame {frame}")
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
                    if self.logger:
                        self.logger.debug(f"[AUDIO_CALLBACK] Processing step: {step}")
                    
                    current_loop_step = step % total_loop_steps
                    for track in self.composition.tracks:
                        if not track.patterns or not track.sequence: continue
                        
                        sequence_index = (step // total_loop_steps) % len(track.sequence)
                        pattern_index = track.sequence[sequence_index]
                        if pattern_index >= len(track.patterns): continue
                        
                        pattern = track.patterns[pattern_index]
                        if not pattern.steps: continue

                        pattern_step = current_loop_step % len(pattern.steps)
                        note_event = pattern.steps[pattern_step]

                        if note_event and note_event.note:
                            instrument = self.instruments.get(track.instrument_id)
                            if instrument:
                                if self.logger:
                                    self.logger.debug(f"[AUDIO_CALLBACK] Note ON: {note_event.note} velocity: {note_event.velocity}")
                                
                                # NOTE ON
                                instrument.note_on(note_event.note, note_event.velocity)
                                
                                # Schedule NOTE OFF
                                duration_in_frames = int(note_event.duration * step_duration_frames)
                                note_off_frame = (step * step_duration_frames) + duration_in_frames
                                
                                # Insert into sorted list to maintain order
                                # Use event counter to ensure unique sorting even for same frame
                                event_tuple = (note_off_frame, self._event_counter, (instrument, note_event.note))
                                bisect.insort(self._note_off_events, event_tuple)
                                self._event_counter += 1
            else:
                if self.logger:
                    self.logger.warning(f"[AUDIO_CALLBACK] step_duration_frames is 0 or negative: {step_duration_frames}")

            # --- 2. Mix audio from all instruments ---
            if self.logger:
                self.logger.debug(f"[AUDIO_CALLBACK] Mixing audio from {len(self.instruments)} instruments")
            
            output_buffer = np.zeros((frames, 1), dtype=np.float32)
            for instrument_id, instrument in self.instruments.items():
                if self.logger:
                    self.logger.debug(f"[AUDIO_CALLBACK] Processing instrument: {instrument_id}, active_notes: {len(instrument.active_notes)}")
                
                try:
                    # Instrument processes its own active notes and returns mixed audio
                    instrument_output = instrument.process(frames)
                    output_buffer += instrument_output.reshape(-1, 1)
                    
                    if self.logger:
                        self.logger.debug(f"[AUDIO_CALLBACK] Instrument {instrument_id} processed successfully")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"[AUDIO_CALLBACK] Error processing instrument {instrument_id}: {e}")

            # --- 3. Finalize and update state ---
            # Simple limiter to prevent clipping
            np.clip(output_buffer, -1.0, 1.0, out=output_buffer)
            
            outdata[:] = output_buffer
            self._current_frame = end_frame
            
            if self.logger:
                self.logger.debug(f"[AUDIO_CALLBACK] Callback completed successfully, current_frame: {self._current_frame}")

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
