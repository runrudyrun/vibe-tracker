import sounddevice as sd
import numpy as np
from src.synthesis import Instrument, SAMPLE_RATE

def play_audio(audio_data):
    """Plays a numpy array of audio data."""
    # Ensure data is in a suitable format (e.g., float32)
    audio_data = audio_data.astype(np.float32)
    sd.play(audio_data, SAMPLE_RATE, blocking=True)

if __name__ == '__main__':
    print("Testing audio playback...")
    
    # Create a simple instrument (default is sine wave)
    basic_instrument = Instrument()
    
    # Play a C4 note (MIDI note number 60) for 1 second
    print("Playing a C4 note for 1 second.")
    note_c4 = basic_instrument.play_note(note_number=60, duration=1.0)
    play_audio(note_c4)
    
    # Play a G4 note (MIDI note number 67) for 0.5 seconds
    print("Playing a G4 note for 0.5 seconds.")
    note_g4 = basic_instrument.play_note(note_number=67, duration=0.5)
    play_audio(note_g4)
    
    print("Test complete.")
