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

def note_to_freq(note_number):
    """Converts a MIDI-like note number to a frequency in Hz."""
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

    def play_note(self, note_number, duration):
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
        frequency = note_to_freq(note_number)
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
