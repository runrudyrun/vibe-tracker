from dataclasses import dataclass, field
from typing import List, Optional

# --- Configuration ---
STEPS_PER_PATTERN = 64  # Default number of steps in a pattern

@dataclass
class NoteEvent:
    """Represents a single note event in a pattern."""
    note: Optional[str] = None  # e.g., 'C4', 'F#5'
    velocity: float = 1.0
    # Duration will be determined by the sequencer's step length

    def to_dict(self):
        return {'note': self.note, 'velocity': self.velocity}

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

@dataclass
class Pattern:
    """A pattern is a sequence of steps, where each step can hold a note."""
    steps: List[Optional[NoteEvent]] = field(default_factory=lambda: [None] * STEPS_PER_PATTERN)

    def to_dict(self):
        return {'steps': [step.to_dict() if step else None for step in self.steps]}

    @classmethod
    def from_dict(cls, data):
        return cls(steps=[NoteEvent.from_dict(step_data) if step_data else None for step_data in data['steps']])

    def set_note(self, step_index: int, note: str, velocity: float = 1.0):
        """Adds or updates a note at a specific step."""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index] = NoteEvent(note=note, velocity=velocity)

    def clear_note(self, step_index: int):
        """Removes a note from a specific step."""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index] = None

@dataclass
class Track:
    """A track contains patterns and is associated with an instrument."""
    instrument_id: str  # Name to link to an Instrument object
    patterns: List[Pattern] = field(default_factory=list)
    sequence: List[int] = field(default_factory=list)  # Sequence of pattern indices to play

    def to_dict(self):
        return {
            'instrument_id': self.instrument_id,
            'patterns': [p.to_dict() for p in self.patterns],
            'sequence': self.sequence
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            instrument_id=data['instrument_id'],
            patterns=[Pattern.from_dict(p_data) for p_data in data['patterns']],
            sequence=data['sequence']
        )

@dataclass
class Composition:
    """The main container for the entire piece of music."""
    bpm: int = 120  # Beats per minute
    tracks: List[Track] = field(default_factory=list)

    def get_step_duration(self) -> float:
        """Calculates the duration of a single step (16th note) in seconds."""
        beats_per_second = self.bpm / 60.0
        steps_per_beat = 4  # Assuming 16th note steps
        steps_per_second = beats_per_second * steps_per_beat
        return 1.0 / steps_per_second

    def to_dict(self):
        return {
            'bpm': self.bpm,
            'tracks': [track.to_dict() for track in self.tracks]
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            bpm=data['bpm'],
            tracks=[Track.from_dict(t_data) for t_data in data['tracks']]
        )
