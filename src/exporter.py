import numpy as np
import wave
import json
from typing import Dict, Optional

from src.music_structures import Composition, NoteEvent
from src.synthesis import Instrument, SAMPLE_RATE

def save_composition_to_json(composition: Composition, instruments: Dict[str, Instrument], filepath: str) -> Optional[str]:
    """Saves the composition and its instruments to a JSON file."""
    try:
        data = {
            'composition': composition.to_dict(),
            'instruments': {name: inst.to_dict() for name, inst in instruments.items()}
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return None
    except Exception as e:
        return f"Error saving JSON: {e}"

def render_composition_to_wav(composition: Composition, instruments: Dict[str, Instrument], filepath: str) -> Optional[str]:
    """Renders a Composition object to a .wav file using an offline sequencer approach."""
    try:
        step_duration_samples = int(composition.get_step_duration() * SAMPLE_RATE)
        if step_duration_samples == 0:
            return "Step duration is zero, cannot render."

        all_pattern_lengths = [len(p.steps) for t in composition.tracks for p in t.patterns if p and p.steps]
        if not all_pattern_lengths:
            return "Composition has no patterns to render."
        total_loop_steps = max(all_pattern_lengths)

        total_samples = total_loop_steps * step_duration_samples
        if total_samples == 0:
            return "Cannot export an empty composition."

        # --- Offline Sequencer Logic ---
        note_on_events = {}
        note_off_events = {}

        for track in composition.tracks:
            instrument = instruments.get(track.instrument_id)
            if not instrument or not track.patterns or not track.sequence:
                continue

            for step in range(total_loop_steps):
                pattern = track.patterns[0] # Assuming one pattern for now
                note_event = pattern.steps[step]

                if note_event and note_event.note:
                    note_on_frame = step * step_duration_samples
                    if note_on_frame not in note_on_events:
                        note_on_events[note_on_frame] = []
                    note_on_events[note_on_frame].append((instrument, note_event))

                    duration_in_frames = note_event.duration * step_duration_samples
                    note_off_frame = note_on_frame + duration_in_frames
                    if note_off_frame not in note_off_events:
                        note_off_events[note_off_frame] = []
                    note_off_events[note_off_frame].append((instrument, note_event.note))

        # --- Audio Processing --- 
        mixdown = np.zeros(total_samples, dtype=np.float32)
        buffer_size = 256 # Process in small chunks

        for i in range(0, total_samples, buffer_size):
            start_frame = i
            # Correctly calculate the size of the current chunk
            current_chunk_size = min(buffer_size, total_samples - start_frame)
            end_frame = start_frame + current_chunk_size

            # Handle note on/off events for this chunk
            for frame in range(start_frame, end_frame):
                if frame in note_on_events:
                    for inst, event in note_on_events[frame]:
                        # The event.note can be a name (e.g., 'C4') or a MIDI number.
                        # The note_on method handles both.
                        inst.note_on(event.note, event.velocity)

                if frame in note_off_events:
                    for inst, note_name in note_off_events[frame]:
                        # For note_off, we must use the specific note name (e.g., 'C4')
                        # that was used to trigger the note.
                        inst.note_off(note_name)

            # Generate audio from all instruments using the correct chunk size
            chunk_buffer = np.zeros(current_chunk_size, dtype=np.float32)
            for instrument in instruments.values():
                chunk_buffer += instrument.process(current_chunk_size)
            
            # Assign the generated chunk to the mixdown buffer
            mixdown[start_frame:end_frame] = chunk_buffer

        # --- Finalization ---
        max_amplitude = np.max(np.abs(mixdown))
        if max_amplitude > 0:
            mixdown /= max_amplitude

        audio_data = (mixdown * 32767).astype(np.int16)

        with wave.open(filepath, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())
        
        return None

    except Exception as e:
        return f"An unexpected error occurred during export: {e}"
