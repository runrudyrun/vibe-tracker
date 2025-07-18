from dataclasses import dataclass, field, fields
from typing import List, Optional

# --- Configuration ---
STEPS_PER_PATTERN = 64  # Default number of steps in a pattern

@dataclass
class NoteEvent:
    """Represents a single note event in a pattern."""
    note: Optional[str] = None  # e.g., 'C4', 'F#5'
    velocity: float = 1.0
    duration: int = 1  # Duration in steps, default to 1 for short notes

    def to_dict(self):
        d = {'note': self.note, 'velocity': self.velocity}
        if self.duration > 1:
            d['duration'] = self.duration
        return d

    @classmethod
    def from_dict(cls, data):
        # Filter the data dictionary to only include keys that are fields in the NoteEvent class
        # This prevents TypeErrors if the LLM sends unexpected fields
        # Use dataclasses.fields() for compatibility with Python 3.10+
        field_names = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in field_names}
        
        # Ensure backward compatibility for data without duration
        filtered_data.setdefault('duration', 1)
        
        return cls(**filtered_data)

@dataclass
class Pattern:
    """A pattern is a sequence of steps, where each step can hold a note."""
    steps: List[Optional[NoteEvent]] = field(default_factory=lambda: [None] * STEPS_PER_PATTERN)

    def to_dict(self):
        return {'steps': [step.to_dict() if step else None for step in self.steps]}

    @classmethod
    def from_dict(cls, data):
        return cls(steps=[NoteEvent.from_dict(step_data) if step_data else None for step_data in data['steps']])

    def set_note(self, step_index: int, note: str, velocity: float = 1.0, duration: int = 1):
        """Adds or updates a note at a specific step."""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index] = NoteEvent(note=note, velocity=velocity, duration=duration)

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
        """Serializes the track to a dictionary format expected by the LLM."""
        notes_list = []
        # Assuming one pattern per track for now, which is how the LLM works
        if self.patterns:
            for step_index, note_event in enumerate(self.patterns[0].steps):
                if note_event and note_event.note:
                    # Correctly use the NoteEvent's own serialization
                    note_dict = note_event.to_dict()
                    note_dict['step'] = step_index
                    notes_list.append(note_dict)
        return {
            'instrument_name': self.instrument_id, # Match LLM's expected key
            'notes': notes_list
        }

    @classmethod
    def from_dict(cls, data):
        """Creates a Track object from the LLM's dictionary format."""
        instrument_id = data['instrument_name'] # Match LLM's expected key
        notes = data.get('notes', [])
        
        new_pattern = Pattern() # Create a single new pattern
        for note_data in notes:
            step = note_data.get('step')
            if step is not None and 'note' in note_data:
                 if 0 <= step < STEPS_PER_PATTERN:
                    # Use the NoteEvent's own deserialization logic
                    new_pattern.steps[step] = NoteEvent.from_dict(note_data)

        # A track will contain just this one pattern, and the sequence will just be [0]
        return cls(instrument_id=instrument_id, patterns=[new_pattern], sequence=[0])

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
