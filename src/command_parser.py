from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ParsedCommand:
    action: Optional[str] = None
    instrument: Optional[str] = None
    target_track_id: Optional[int] = None
    style: Optional[str] = None
    tempo_qualifier: Optional[str] = None # e.g., 'fast', 'slow'
    duration_bars: Optional[int] = None
    filename: Optional[str] = None
    raw_text: str = ''

def parse_command(text: str) -> ParsedCommand:
    """Parses a natural language command into a structured format.
    
    This is a simple keyword-based implementation.
    """
    lower_text = text.lower()
    words = lower_text.split()
    
    command = ParsedCommand(raw_text=text)

    # Keywords for different aspects
    ACTIONS = {'create', 'make', 'add', 'generate', 'play', 'delete', 'remove', 'save', 'load', 'export', 'render'}
    INSTRUMENTS = {'kick', 'drum', 'bass', 'lead', 'synth', 'snare', 'hat'}
    STYLES = {'techno', 'house', 'hip-hop', 'ambient'}
    TEMPO_MODS = {'fast': 140, 'slow': 90, 'medium': 120}

    # --- Simple keyword matching ---
    for i, word in enumerate(words):
        if word in ACTIONS:
            command.action = word
            # For save/load, the next word is the filename
            if command.action in ['save', 'load', 'export', 'render'] and i + 1 < len(words):
                command.filename = words[i+1]
        if word in INSTRUMENTS:
            command.instrument = word
        if word in STYLES:
            command.style = word
        if word in TEMPO_MODS:
            command.tempo_qualifier = word

    # --- Extract duration (e.g., "4 bars") ---
    try:
        if 'bar' in lower_text or 'bars' in lower_text:
            for i, word in enumerate(words):
                if word.isdigit() and (words[i+1] in ['bar', 'bars']):
                    command.duration_bars = int(word)
                    break
    except (ValueError, IndexError):
        pass # Ignore if parsing fails

    # --- Extract target for deletion (e.g., "delete 1") ---
    if command.action in ['delete', 'remove']:
        try:
            for word in words:
                if word.isdigit():
                    command.target_track_id = int(word)
                    break
        except (ValueError, IndexError):
            pass

    # If no action is found, assume 'create'
    if not command.action:
        command.action = 'create'

    return command

# --- Test cases ---
if __name__ == '__main__':
    tests = [
        "create a fast techno kick for 8 bars",
        "make a slow ambient synth",
        "add a house bass line",
        "generate a kick drum",
        "just a simple snare please"
    ]

    for test in tests:
        parsed = parse_command(test)
        print(f'Raw: "{test}"\nParsed: {parsed}\n')
