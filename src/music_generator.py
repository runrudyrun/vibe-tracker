from src.command_parser import ParsedCommand
from src.music_structures import Pattern

# --- Note Definitions (MIDI-like) ---
KICK_NOTE = 36  # C2
SNARE_NOTE = 38 # D2
HAT_NOTE = 42   # F#2

def generate_pattern(command: ParsedCommand) -> Pattern:
    """Generates a musical pattern based on a parsed command."""
    pattern = Pattern() # Creates a pattern with 64 steps

    # --- Rule-based Generation ---

    if command.instrument in ['kick', 'drum']:
        # Simple Techno/House kick: 4-on-the-floor
        if command.style in ['techno', 'house'] or not command.style:
            for step in range(0, 64, 16):
                pattern.set_note(step, KICK_NOTE)

    if command.instrument == 'snare':
        # Classic snare on the 2 and 4
        for step in range(16, 64, 32):
            pattern.set_note(step, SNARE_NOTE)
    
    if command.instrument == 'hat':
        # Simple 8th note hi-hats
        for step in range(0, 64, 8):
            pattern.set_note(step, HAT_NOTE)

    # More rules for different instruments and styles can be added here.

    return pattern


if __name__ == '__main__':
    print("Testing music generator...")
    
    # Test 1: Techno Kick
    cmd1 = ParsedCommand(action='create', instrument='kick', style='techno')
    p1 = generate_pattern(cmd1)
    print(f"\nGenerated for: {cmd1}")
    print("Notes at steps:", [i for i, note in enumerate(p1.steps) if note])

    # Test 2: Snare
    cmd2 = ParsedCommand(action='create', instrument='snare')
    p2 = generate_pattern(cmd2)
    print(f"\nGenerated for: {cmd2}")
    print("Notes at steps:", [i for i, note in enumerate(p2.steps) if note])

    # Test 3: Hi-hat
    cmd3 = ParsedCommand(action='create', instrument='hat')
    p3 = generate_pattern(cmd3)
    print(f"\nGenerated for: {cmd3}")
    print("Notes at steps:", [i for i, note in enumerate(p3.steps) if note])
