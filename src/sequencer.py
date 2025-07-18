import time
import threading
import numpy as np
import sounddevice as sd

from .music_structures import Composition
from .synthesis import SAMPLE_RATE


class Sequencer:
    """Plays a Composition object using a callback-based audio stream."""

    def __init__(self, composition: Composition, instruments: dict):
        self._lock = threading.Lock()
        self.composition = composition
        self.instruments = instruments

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
        if status:
            print(status)

        with self._lock:
            # 1. Calculate time boundaries for this callback
            start_frame = self._current_frame
            end_frame = start_frame + frames
            step_duration_frames = int(self.composition.get_step_duration() * SAMPLE_RATE)

            # 2. Check for new notes to trigger in this time block
            if step_duration_frames > 0:
                start_step = start_frame // step_duration_frames
                end_step = end_frame // step_duration_frames

                for step in range(start_step, end_step + 1):
                    for track in self.composition.tracks:
                        if not track.patterns: continue
                        pattern = track.patterns[0]
                        note_event = pattern.steps[step % len(pattern.steps)]

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

