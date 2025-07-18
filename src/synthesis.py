import numpy as np

# --- Configuration ---
SAMPLE_RATE = 44100  # Samples per second

# --- Waveform Generators ---

def sine_wave(frequency, duration):
    """Generates a sine wave."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    return np.sin(frequency * t * 2 * np.pi)

def square_wave(frequency, duration):
    """Generates a square wave."""
    return np.sign(sine_wave(frequency, duration))

def sawtooth_wave(frequency, duration):
    """Generates a sawtooth wave."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    return 2 * (t * frequency - np.floor(0.5 + t * frequency))

def triangle_wave(frequency, duration):
    """Generates a triangle wave."""

def white_noise(duration):
    """Generates white noise."""
    return np.random.uniform(-1, 1, int(SAMPLE_RATE * duration))
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    return 2 * np.abs(sawtooth_wave(frequency, duration)) - 1

# --- Note to Frequency Conversion ---

# A4 is 440 Hz, which is the 49th key on a standard piano (starting from A0)
NOTE_OFFSET = 49
A4_FREQ = 440.0

def note_name_to_key_number(note_name: str) -> int:
    """Converts a note name like 'C4' or 'F#5' to a piano key number (A0=1, A4=49)."""
    if not isinstance(note_name, str) or len(note_name) < 2:
        return 49  # Default to A4 if format is invalid

    note_map = {'C': -8, 'C#': -7, 'D': -6, 'D#': -5, 'E': -4, 'F': -3, 'F#': -2, 'G': -1, 'G#': 0, 'A': 1, 'A#': 2, 'B': 3}
    
    octave_str = note_name[-1]
    note_part = note_name[:-1].upper()

    if not octave_str.isdigit() or note_part not in note_map:
        return 49 # Default to A4

    octave = int(octave_str)
    key_number = note_map[note_part] + (octave - 4) * 12 + NOTE_OFFSET
    return key_number

def note_to_freq(note_number):
    """Converts a piano key number to a frequency in Hz."""
    return A4_FREQ * (2 ** ((note_number - NOTE_OFFSET) / 12.0))

# --- Instrument Class (Placeholder) ---

class Instrument:
    """Represents a sound generator with a specific waveform and envelope."""
    def __init__(self, waveform_func=sine_wave, attack=0.01, decay=0.1, sustain_level=0.7, release=0.2):
        self.waveform_func = waveform_func
        self.attack = attack
        self.decay = decay
        self.sustain_level = sustain_level
        self.release = release

    def play_note(self, note: str, duration: float):
        # For noise, frequency is irrelevant
        if self.waveform_func == white_noise:
            wave = self.waveform_func(duration)
            # Apply ADSR envelope
            total_samples = int(duration * SAMPLE_RATE)
            envelope = np.zeros(total_samples)

            attack_samples = int(self.attack * SAMPLE_RATE)
            decay_samples = int(self.decay * SAMPLE_RATE)
            release_samples = int(self.release * SAMPLE_RATE)
            sustain_samples = total_samples - attack_samples - decay_samples - release_samples

            if sustain_samples < 0:
                # If duration is shorter than attack + decay + release, scale them down
                total_envelope_time = self.attack + self.decay + self.release
                # Avoid division by zero if total_envelope_time is 0
                scale_factor = duration / total_envelope_time if total_envelope_time > 0 else 0
                attack_samples = int(self.attack * scale_factor * SAMPLE_RATE)
                decay_samples = int(self.decay * scale_factor * SAMPLE_RATE)
                # The rest is release
                sustain_samples = 0
                release_samples = total_samples - attack_samples - decay_samples
                if release_samples < 0: release_samples = 0

            # Attack phase
            if attack_samples > 0:
                envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

            # Decay phase
            if decay_samples > 0:
                start = attack_samples
                end = start + decay_samples
                envelope[start:end] = np.linspace(1, self.sustain_level, decay_samples)

            # Sustain phase
            if sustain_samples > 0:
                start = attack_samples + decay_samples
                end = start + sustain_samples
                envelope[start:end] = self.sustain_level

            # Release phase
            if release_samples > 0:
                start = total_samples - release_samples
                envelope[start:] = np.linspace(self.sustain_level, 0, release_samples)

            return wave * envelope

        """Generates the audio data for a given note and duration."""
        key_number = note_name_to_key_number(note)
        frequency = note_to_freq(key_number)
        wave = self.waveform_func(frequency, duration)

        # Apply ADSR envelope
        total_samples = int(duration * SAMPLE_RATE)
        envelope = np.zeros(total_samples)

        attack_samples = int(self.attack * SAMPLE_RATE)
        decay_samples = int(self.decay * SAMPLE_RATE)
        release_samples = int(self.release * SAMPLE_RATE)
        sustain_samples = total_samples - attack_samples - decay_samples - release_samples

        if sustain_samples < 0:
            # If duration is shorter than attack + decay + release, scale them down
            total_envelope_time = self.attack + self.decay + self.release
            scale_factor = duration / total_envelope_time
            attack_samples = int(self.attack * scale_factor * SAMPLE_RATE)
            decay_samples = int(self.decay * scale_factor * SAMPLE_RATE)
            # The rest is release
            sustain_samples = 0
            release_samples = total_samples - attack_samples - decay_samples
            if release_samples < 0: release_samples = 0

        # Attack phase
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

        # Decay phase
        if decay_samples > 0:
            start = attack_samples
            end = start + decay_samples
            envelope[start:end] = np.linspace(1, self.sustain_level, decay_samples)

        # Sustain phase
        if sustain_samples > 0:
            start = attack_samples + decay_samples
            end = start + sustain_samples
            envelope[start:end] = self.sustain_level

        # Release phase
        if release_samples > 0:
            start = total_samples - release_samples
            envelope[start:] = np.linspace(self.sustain_level, 0, release_samples)

        return wave * envelope
