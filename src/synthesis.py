import numpy as np
from scipy.signal import butter, lfilter
import time
import logging

# --- Configuration ---
SAMPLE_RATE = 44100  # Samples per second

# --- Waveform Generators (Stateful) ---
# These now act as generators, producing samples on demand.

def sine_wave(frequency):
    """Generates a continuous sine wave at a given frequency."""
    increment = (2 * np.pi * frequency) / SAMPLE_RATE
    phase = 0
    while True:
        yield np.sin(phase)
        phase += increment

def poly_blep(phase, phase_increment):
    """A polynomial approximation of a band-limited step function."""
    # phase is the current phase of the oscillator.
    # phase_increment is the phase change per sample.
    # The function checks if the phase is near a discontinuity (0 or 1) and applies a correction.
    
    # Check for discontinuity at phase 0
    if phase < phase_increment:
        t = phase / phase_increment
        return t + t - t * t - 1.0
    # Check for discontinuity at phase 1 (the wrap-around point)
    elif phase > 1.0 - phase_increment:
        t = (phase - 1.0) / phase_increment
        return t * t + t + t + 1.0
    # No discontinuity, no correction needed
    else:
        return 0.0

def sawtooth_wave(frequency):
    """Generates a continuous, anti-aliased sawtooth wave using PolyBLEP."""
    phase = 0.0
    phase_increment = frequency / SAMPLE_RATE
    while True:
        # Naive sawtooth wave
        saw = 2.0 * phase - 1.0
        # Apply PolyBLEP correction
        saw -= poly_blep(phase, phase_increment)
        yield saw
        phase += phase_increment
        if phase >= 1.0:
            phase -= 1.0

def square_wave(frequency):
    """Generates a continuous, anti-aliased square wave using PolyBLEP."""
    phase = 0.0
    phase_increment = frequency / SAMPLE_RATE
    while True:
        # Naive square wave (1 for first half, -1 for second half)
        square = 1.0 if phase < 0.5 else -1.0
        # Apply PolyBLEP correction at both discontinuities (0 and 0.5)
        square += poly_blep(phase, phase_increment)
        # The phase for the second discontinuity is shifted by 0.5
        square -= poly_blep((phase + 0.5) % 1.0, phase_increment)
        yield square
        phase += phase_increment
        if phase >= 1.0:
            phase -= 1.0

def triangle_wave(frequency):
    """Generates a continuous triangle wave."""
    for sample in sawtooth_wave(frequency):
        yield 2 * np.abs(sample) - 1

def white_noise(frequency):
    """Generates continuous white noise. Frequency is ignored."""
    while True:
        yield np.random.uniform(-1, 1)

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
        return 49
    note_map = {'C': -8, 'C#': -7, 'D': -6, 'D#': -5, 'E': -4, 'F': -3, 'F#': -2, 'G': -1, 'G#': 0, 'A': 1, 'A#': 2, 'B': 3}
    octave_str = note_name[-1]
    note_part = note_name[:-1].upper()
    if not octave_str.isdigit() or note_part not in note_map:
        return 49
    octave = int(octave_str)
    return note_map[note_part] + (octave - 4) * 12 + NOTE_OFFSET

def note_to_freq(note_number):
    """Converts a piano key number to a frequency in Hz."""
    return A4_FREQ * (2 ** ((note_number - NOTE_OFFSET) / 12.0))

# --- Real-time Synthesis Components ---

class ADSREnvelope:
    """Stateful ADSR envelope generator."""
    def __init__(self, attack, decay, sustain_level, release):
        self.attack_rate = 1 / (attack * SAMPLE_RATE) if attack > 0 else float('inf')
        self.decay_rate = (1 - sustain_level) / (decay * SAMPLE_RATE) if decay > 0 else float('inf')
        self.release_time = release
        self.release_rate = 0 # Will be calculated on note_off
        self.sustain_level = sustain_level
        self.state = 'off'
        self.level = 0.0

    def note_on(self):
        self.state = 'attack'

    def note_off(self):
        # Release rate is calculated based on the current level when the note is released.
        if self.release_time > 0:
            self.release_rate = self.level / (self.release_time * SAMPLE_RATE)
        else:
            self.release_rate = float('inf') # Instant release
        self.state = 'release'

    def process(self):
        """Generator that yields the next envelope level indefinitely."""
        while True:
            if self.state == 'attack':
                self.level += self.attack_rate
                if self.level >= 1.0:
                    self.level = 1.0
                    self.state = 'decay'
            elif self.state == 'decay':
                self.level -= self.decay_rate
                if self.level <= self.sustain_level:
                    self.level = self.sustain_level
                    self.state = 'sustain'
            elif self.state == 'sustain':
                self.level = self.sustain_level
            elif self.state == 'release':
                self.level -= self.release_rate
                if self.level <= 0:
                    self.level = 0
                    self.state = 'off'
            else: # off
                self.level = 0.0
            yield self.level

class ActiveNote:
    """Represents a single, currently sounding note."""
    def __init__(self, note_name, velocity, instrument):
        self.note_name = note_name
        self.velocity = velocity
        self.instrument = instrument
        self.frequency = note_to_freq(note_name_to_key_number(note_name))

        # Create stateful generators for each oscillator
        self.oscillators = []
        for osc_params in self.instrument.oscillators:
            waveform_func = get_waveform_function(osc_params.get('waveform', 'sine'))
            self.oscillators.append({
                'generator': waveform_func(self.frequency),
                'amplitude': osc_params.get('amplitude', 1.0)
            })

        # Create and start the envelope
        self.envelope = ADSREnvelope(instrument.attack, instrument.decay, instrument.sustain_level, instrument.release)
        self.envelope_gen = self.envelope.process()
        self.envelope.note_on()

    def note_off(self):
        self.envelope.note_off()

    def is_active(self):
        return self.envelope.state != 'off'

    def process(self, num_samples):
        """Generates a block of audio for this note by mixing oscillators."""
        if not self.is_active():
            return np.zeros(num_samples)

        # Get envelope values
        envelope_samples = np.array([next(self.envelope_gen) for _ in range(num_samples)])

        # Generate and mix samples from all oscillators
        mixed_wave = np.zeros(num_samples)
        for osc in self.oscillators:
            wave_samples = np.array([next(osc['generator']) for _ in range(num_samples)])
            mixed_wave += wave_samples * osc['amplitude']

        # Normalize if necessary (e.g., if total amplitude > 1.0)
        total_amplitude = sum(osc['amplitude'] for osc in self.oscillators)
        if total_amplitude > 1.0:
            mixed_wave /= total_amplitude

        # Apply envelope to the mixed wave
        wave = mixed_wave * envelope_samples

        # Apply filter if specified
        if self.instrument.filter_type and self.instrument.filter_type != 'none':
            wave = apply_filter(
                wave,
                cutoff_hz=self.instrument.filter_cutoff_hz,
                resonance_q=self.instrument.filter_resonance_q,
                filter_type=self.instrument.filter_type
            )
        return wave * self.velocity

def apply_filter(signal, cutoff_hz, resonance_q, filter_type='lowpass', order=2):
    """Applies a filter to a signal."""
    nyquist = 0.5 * SAMPLE_RATE
    normal_cutoff = cutoff_hz / nyquist

    if normal_cutoff >= 1.0:
        return signal # Return original signal if cutoff is at or above Nyquist

    if filter_type == 'lowpass':
        b, a = butter(order, normal_cutoff, btype='low', analog=False, fs=None)
        y = lfilter(b, a, signal)
        return y
    elif filter_type == 'highpass':
        b, a = butter(order, normal_cutoff, btype='high', analog=False, fs=None)
        y = lfilter(b, a, signal)
        return y
    # Add other filter types like 'bandpass', 'bandstop' here in the future
    return signal

class Instrument:
    """Manages and synthesizes sound for multiple active notes using multiple oscillators."""
    def __init__(self, name="default", oscillators=None, attack=0.01, decay=0.1, sustain_level=0.7, release=0.2, filter_type=None, filter_cutoff_hz=20000, filter_resonance_q=0.707):
        self.name = name
        # Default to a single sine wave oscillator for backward compatibility
        if oscillators is None:
            self.oscillators = [{'waveform': 'sine', 'amplitude': 1.0}]
        else:
            self.oscillators = oscillators
        
        self.attack = attack
        self.decay = decay
        self.sustain_level = sustain_level
        self.release = release

        # Filter parameters
        self.filter_type = filter_type
        self.filter_cutoff_hz = filter_cutoff_hz
        self.filter_resonance_q = filter_resonance_q

        self.active_notes = []

    def to_dict(self):
        """Serializes the instrument to a dictionary."""
        return {
            'name': self.name,
            'oscillators': self.oscillators,
            'attack': self.attack,
            'decay': self.decay,
            'sustain_level': self.sustain_level,
            'release': self.release,
            'filter_type': self.filter_type,
            'filter_cutoff_hz': self.filter_cutoff_hz,
            'filter_resonance_q': self.filter_resonance_q
        }

    @classmethod
    def from_dict(cls, data):
        """Creates an Instrument object from a dictionary.
           Supports both old ('waveform') and new ('oscillators') formats."""
        
        oscillators = data.get('oscillators')
        # Backward compatibility: if 'oscillators' is missing, check for 'waveform'
        if oscillators is None:
            waveform_name = data.get('waveform', 'sine')
            oscillators = [{'waveform': waveform_name, 'amplitude': 1.0}]
            
        return cls(
            name=data.get('name', 'default'),
            oscillators=oscillators,
            attack=data.get('attack', 0.01),
            decay=data.get('decay', 0.1),
            sustain_level=data.get('sustain_level', 0.7),
            release=data.get('release', 0.2),
            filter_type=data.get('filter_type'),
            filter_cutoff_hz=data.get('filter_cutoff_hz', 20000),
            filter_resonance_q=data.get('filter_resonance_q', 0.707)
        )

    def note_on(self, note_name: str, velocity: float = 1.0):
        # CRITICAL FIX: The previous logic of re-triggering an envelope was flawed because
        # the underlying generator (envelope_gen) could be exhausted. The correct, robust
        # approach is to remove the old note instance and create a fresh one.

        # Remove any existing note with the same name, active or not.
        self.active_notes = [n for n in self.active_notes if n.note_name != note_name]

        # Create a new, fresh ActiveNote instance and add it to the list.
        new_note = ActiveNote(note_name, velocity, self)
        self.active_notes.append(new_note)

    def note_off(self, note_name: str):
        for note in self.active_notes:
            if note.note_name == note_name:
                note.note_off()

    def process(self, num_samples: int):
        """Mixes all active notes into a single audio buffer."""
        logger = logging.getLogger(__name__)
        
        logger.debug(f"[INSTRUMENT] {self.name} - Processing {num_samples} samples, active_notes: {len(self.active_notes)}")
        
        output_buffer = np.zeros(num_samples)
        # Process notes and remove inactive ones
        notes_to_keep = []
        
        for i, note in enumerate(self.active_notes):
            logger.debug(f"[INSTRUMENT] {self.name} - Processing note {i}: {note.note_name}, is_active: {note.is_active()}")
            
            if note.is_active():
                try:
                    note_output = note.process(num_samples)
                    output_buffer += note_output
                    notes_to_keep.append(note)
                    logger.debug(f"[INSTRUMENT] {self.name} - Note {note.note_name} processed successfully")
                except Exception as e:
                    logger.error(f"[INSTRUMENT] {self.name} - Error processing note {note.note_name}: {e}")
                    # Remove problematic note by setting envelope to off state
                    note.envelope.state = 'off'
            else:
                logger.debug(f"[INSTRUMENT] {self.name} - Removing inactive note: {note.note_name}")
        
        self.active_notes = notes_to_keep
        logger.debug(f"[INSTRUMENT] {self.name} - Kept {len(notes_to_keep)} active notes")
        
        # Apply filter if specified
        if self.filter_type and len(output_buffer) > 0:
            logger.debug(f"[INSTRUMENT] {self.name} - Applying {self.filter_type} filter")
            try:
                output_buffer = apply_filter(
                    output_buffer, 
                    self.filter_cutoff_hz, 
                    self.filter_resonance_q, 
                    self.filter_type
                )
                logger.debug(f"[INSTRUMENT] {self.name} - Filter applied successfully")
            except Exception as e:
                logger.error(f"[INSTRUMENT] {self.name} - Error applying filter: {e}")
        
        logger.debug(f"[INSTRUMENT] {self.name} - Process completed")
        return output_buffer
