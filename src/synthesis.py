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
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    return 2 * np.abs(sawtooth_wave(frequency, duration)) - 1

def white_noise(frequency, duration):
    """Generates white noise. Frequency is ignored."""
    return np.random.uniform(-1, 1, int(SAMPLE_RATE * duration))

WAVEFORM_MAP = {
    'sine': sine_wave,
    'square': square_wave,
    'sawtooth': sawtooth_wave,
    'triangle': triangle_wave,
    'noise': white_noise,
}

def get_waveform_function(name: str):
    """Returns the waveform function based on its name."""
    return WAVEFORM_MAP.get(name.lower(), sine_wave)

# --- Note to Frequency Conversion ---
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

# --- Sound Processing ---

def apply_envelope(audio, attack, decay, sustain_level, release, sample_rate):
    """Applies an ADSR envelope to an audio signal."""
    total_samples = len(audio)
    envelope = np.zeros(total_samples)

    attack_samples = int(attack * sample_rate)
    decay_samples = int(decay * sample_rate)
    release_samples = int(release * sample_rate)
    sustain_samples = total_samples - attack_samples - decay_samples - release_samples

    # If the note is shorter than the attack+decay+release, scale them down
    if sustain_samples < 0:
        # Proportional scaling
        total_adsr_time = attack + decay + release
        if total_adsr_time > 0:
            ratio = (total_samples / sample_rate) / total_adsr_time
            attack_samples = int(attack * ratio * sample_rate)
            decay_samples = int(decay * ratio * sample_rate)
            release_samples = int(release * ratio * sample_rate)
            # The rest is sustain, which will be 0 or very small
            sustain_samples = total_samples - attack_samples - decay_samples - release_samples
        else:
            # If all times are zero, do nothing
            attack_samples = decay_samples = release_samples = sustain_samples = 0

    # Ensure total samples match up to avoid off-by-one errors from rounding
    current_total = attack_samples + decay_samples + sustain_samples + release_samples
    if current_total != total_samples:
        sustain_samples += total_samples - current_total

    # Build the envelope
    start = 0
    if attack_samples > 0:
        envelope[start:start + attack_samples] = np.linspace(0, 1, attack_samples)
        start += attack_samples

    if decay_samples > 0:
        envelope[start:start + decay_samples] = np.linspace(1, sustain_level, decay_samples)
        start += decay_samples

    # Sustain phase
    if sustain_samples > 0:
        start = attack_samples + decay_samples
        end = start + sustain_samples
        envelope[start:end] = sustain_level

    # Release phase
    if release_samples > 0:
        start = total_samples - release_samples
        envelope[start:] = np.linspace(sustain_level, 0, release_samples)

    return audio * envelope

# --- Instrument Class ---

class Instrument:
    """Represents a sound generator with a specific waveform and envelope."""
    def __init__(self, waveform_func=sine_wave, attack=0.01, decay=0.1, sustain_level=0.7, release=0.2):
        self.waveform_func = waveform_func
        self.attack = attack
        self.decay = decay
        self.sustain_level = sustain_level
        self.release = release

    def play_note(self, note: str, duration: float):
        """Generates the audio data for a given note and duration."""
        key_number = note_name_to_key_number(note)
        frequency = note_to_freq(key_number)
        
        # Generate the basic waveform
        wave = self.waveform_func(frequency, duration)
        
        # Apply the ADSR envelope
        return apply_envelope(wave, self.attack, self.decay, self.sustain_level, self.release, SAMPLE_RATE)
