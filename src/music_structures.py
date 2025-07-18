from dataclasses import dataclass, field
from typing import List, Optional

# --- Configuration ---
STEPS_PER_PATTERN = 64  # Default number of steps in a pattern

@dataclass
class NoteEvent:
    """Represents a single note event in a pattern."""
    note_number: int  # MIDI-like note number (e.g., 60 for C4)
    volume: float = 1.0  # Velocity/volume from 0.0 to 1.0
    # Duration will be determined by the sequencer's step length

@dataclass
class Pattern:
    """A pattern is a sequence of steps, where each step can hold a note."""
    steps: List[Optional[NoteEvent]] = field(default_factory=lambda: [None] * STEPS_PER_PATTERN)

    def set_note(self, step_index: int, note_number: int, volume: float = 1.0):
        """Adds or updates a note at a specific step."""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index] = NoteEvent(note_number=note_number, volume=volume)

    def clear_note(self, step_index: int):
        """Removes a note from a specific step."""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index] = None

@dataclass
class Track:
    """A track contains patterns and is associated with an instrument."""
    instrument_id: int  # ID to link to an Instrument object
    patterns: List[Pattern] = field(default_factory=list)
    sequence: List[int] = field(default_factory=list)  # Sequence of pattern indices to play

@dataclass
class Composition:
    """The main container for the entire piece of music."""
    bpm: int = 120  # Beats per minute
    tracks: List[Track] = field(default_factory=list)

    def get_step_duration_seconds(self) -> float:
        """Calculates the duration of a single step (16th note) in seconds."""
        beats_per_second = self.bpm / 60.0
        steps_per_beat = 4  # Assuming 16th note steps
        steps_per_second = beats_per_second * steps_per_beat
        return 1.0 / steps_per_second
