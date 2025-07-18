import numpy as np
import wave
from typing import Dict, Optional

from src.music_structures import Composition
from src.synthesis import Instrument

SAMPLE_RATE = 44100

def render_composition_to_wav(composition: Composition, instruments: Dict[str, Instrument], filepath: str) -> Optional[str]:
    """Renders a Composition object to a .wav file.

    Args:
        composition: The composition to render.
        instruments: A dictionary mapping instrument names to Instrument objects.
        filepath: The path for the output .wav file.

    Returns:
        None if successful, or an error message string if an error occurs.
    """
    try:
        step_duration_samples = int(composition.get_step_duration() * SAMPLE_RATE)
        
        # Find the maximum number of steps from any pattern in the composition
        num_steps = 0
        for track in composition.tracks:
            for pattern in track.patterns:
                num_steps = max(num_steps, len(pattern.steps))

        total_samples = num_steps * step_duration_samples
        if total_samples == 0:
            return "Cannot export an empty composition."

        # Mixdown buffer
        mixdown = np.zeros(total_samples, dtype=np.float32)

        for track in composition.tracks:
            instrument = instruments.get(track.instrument_id)
            if not instrument:
                continue

            track_audio = np.zeros(total_samples, dtype=np.float32)
            current_pos = 0

            # For simplicity, we'll just render the first pattern of each track
            if not track.patterns:
                continue
            pattern = track.patterns[0]

            for step in pattern.steps:
                if step.note:
                    note_audio = instrument.play_note(step.note, composition.get_step_duration())
                    end_sample = min(current_pos + len(note_audio), len(track_audio))
                    track_audio[current_pos:end_sample] += note_audio[:end_sample - current_pos]
                current_pos += step_duration_samples

            mixdown += track_audio

        # Normalize audio to prevent clipping
        max_amplitude = np.max(np.abs(mixdown))
        if max_amplitude > 0:
            mixdown /= max_amplitude

        # Convert to 16-bit PCM
        audio_data = (mixdown * 32767).astype(np.int16)

        # Write to .wav file
        with wave.open(filepath, 'w') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())
        
        return None

    except Exception as e:
        return f"An unexpected error occurred during export: {e}"
