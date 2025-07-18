import time
import threading
import numpy as np
import sounddevice as sd

from .music_structures import Composition
from .synthesis import SAMPLE_RATE


class Sequencer:
    """Plays a Composition object using a callback-based audio stream."""

    def __init__(self, composition: Composition, instruments: dict, logger=None):
        self._lock = threading.Lock()
        self.composition = composition
        self.instruments = instruments
        self.logger = logger

        self.is_playing = False
        self._stream = None
        self._current_frame = 0
        self._active_notes = [] # List of (start_frame, end_frame, audio_generator)

    def update_composition(self, new_composition, new_instruments):
        """Thread-safely update the composition and instruments."""
        with self._lock:
            self.composition = new_composition
            self.instruments = new_instruments
            self._current_frame = 0 # Reset playback position

    def _audio_callback(self, outdata, frames, time, status):
        """The heart of the sequencer. Called by the audio driver to get samples."""
        # if status:
        #     print(status) # This can be noisy, disable for now

        with self._lock:
            # 1. Calculate time boundaries for this callback
            start_frame = self._current_frame
            end_frame = start_frame + frames
            step_duration_frames = int(self.composition.get_step_duration() * SAMPLE_RATE)

            # 2. Check for new notes to trigger in this time block
            if step_duration_frames > 0:
                # Determine the total length of the composition loop in steps.
                # We'll use the length of the first pattern of the first track as the master length.
                # A more robust solution might define this in the Composition object itself.
                # Find the longest pattern in the composition to determine the master loop length.
                all_pattern_lengths = [len(p.steps) for t in self.composition.tracks for p in t.patterns if p.steps]
                total_loop_steps = max(all_pattern_lengths) if all_pattern_lengths else 64

                start_step = start_frame // step_duration_frames
                end_step = end_frame // step_duration_frames

                # --- DEBUG LOGGING ---
                if self.logger and start_step > 0 and start_step % total_loop_steps == 0:
                    self.logger.debug(f"Loop Start: Step={start_step}, TotalSteps={total_loop_steps}, Frame={self._current_frame}")

                for step in range(start_step, end_step + 1):
                    current_loop_step = step % total_loop_steps

                    for track in self.composition.tracks:
                        if not track.patterns or not track.sequence:
                            continue

                        # Determine which pattern from the sequence to play
                        sequence_index = (step // total_loop_steps) % len(track.sequence)
                        pattern_index = track.sequence[sequence_index]
                        
                        if pattern_index >= len(track.patterns):
                            continue # Sequence points to a non-existent pattern

                        pattern = track.patterns[pattern_index]

                        # If the pattern has notes, calculate the current step within that pattern using modulo
                        # This makes shorter patterns loop correctly within the main composition loop.
                        if pattern.steps:
                            pattern_length = len(pattern.steps)
                            pattern_step = current_loop_step % pattern_length
                            note_event = pattern.steps[pattern_step]

                            if note_event and note_event.note:
                                instrument = self.instruments.get(track.instrument_id)
                                if instrument:
                                    note_start_frame = step * step_duration_frames
                                    audio_data = instrument.play_note(note_event.note, self.composition.get_step_duration())
                                    audio_data *= note_event.velocity
                                    self._active_notes.append((note_start_frame, audio_data))

            # 3. Mix audio for the current block
            output_buffer = np.zeros((frames, 1), dtype=np.float32)
            remaining_notes = []
            for note_start_frame, note_audio in self._active_notes:
                # Position of the note relative to the start of the callback block
                note_pos_in_block = note_start_frame - start_frame
                
                # Slices for copying audio into the output buffer
                slice_in_note = slice(max(0, -note_pos_in_block), len(note_audio))
                slice_in_buffer = slice(max(0, note_pos_in_block), min(frames, note_pos_in_block + len(note_audio)))
                
                # If the note is still relevant, mix it in
                if slice_in_buffer.start < slice_in_buffer.stop:
                    # Adjust slice_in_note based on how much of the note fits in the buffer
                    note_audio_segment = note_audio[slice_in_note]
                    needed_len = slice_in_buffer.stop - slice_in_buffer.start
                    output_buffer[slice_in_buffer, 0] += note_audio_segment[:needed_len]
                    
                    # If the note continues past this buffer, keep it
                    if (note_start_frame + len(note_audio)) > end_frame:
                        remaining_notes.append((note_start_frame, note_audio))

            self._active_notes = remaining_notes
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
        self._active_notes.clear()
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
    # --- Create a test composition ---
    print("Creating a test composition...")
    
    # 1. Instruments
    # A simple sine wave for a kick drum sound (low frequency)
    kick_instrument = Instrument(waveform_func=sine_wave, attack=0.01, decay=0.15, sustain_level=0, release=0.1)
    instruments = {'kick': kick_instrument}

    # 2. Pattern
    # A classic 4/4 kick drum pattern
    kick_pattern = Pattern()
    kick_note = 'C2' # A common kick drum note
    kick_pattern.set_note(0, kick_note)
    kick_pattern.set_note(16, kick_note)
    kick_pattern.set_note(32, kick_note)
    kick_pattern.set_note(48, kick_note)

    # 3. Track
    kick_track = Track(instrument_id='kick', patterns=[kick_pattern])

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

