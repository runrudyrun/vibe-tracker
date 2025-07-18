from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Input, RichLog, Static

# --- Project Imports ---
from src.command_parser import parse_command
from src.music_generator import generate_pattern
from src.music_structures import Composition, Track
from src.sequencer import Sequencer
from src.synthesis import Instrument, sine_wave, white_noise
from src.project_manager import save_project, load_project
from src.exporter import render_composition_to_wav

class MusicEngine:
    """Manages the musical state of the application."""
    def __init__(self):
        self.composition = Composition(bpm=120)
        self.instruments = self._create_default_instruments()
        self.sequencer = Sequencer(self.composition, self.instruments)
        self.next_track_id = 0

    def _create_default_instruments(self):
        """Create a bank of default instruments."""
        return {
            'kick': Instrument(waveform_func=sine_wave, attack=0.01, decay=0.2, sustain_level=0, release=0.1),
            'snare': Instrument(waveform_func=white_noise, attack=0.01, decay=0.15, sustain_level=0.1, release=0.1),
            'hat': Instrument(waveform_func=white_noise, attack=0.005, decay=0.05, sustain_level=0, release=0.05),
        }

    def process_command(self, command_text: str):
        """Parses a command, generates music, and updates the composition."""
        parsed_cmd = parse_command(command_text)

        # --- Handle Save/Load --- #
        if parsed_cmd.action == 'save':
            if not parsed_cmd.filename:
                return "Please specify a filename, e.g., 'save my_song.json'."
            filename = parsed_cmd.filename if parsed_cmd.filename.endswith('.json') else f"{parsed_cmd.filename}.json"
            error = save_project(self.composition, filename)
            return f"Project saved to {filename}." if not error else f"Error: {error}"

        if parsed_cmd.action == 'load':
            if not parsed_cmd.filename:
                return "Please specify a filename, e.g., 'load my_song.json'."
            filename = parsed_cmd.filename if parsed_cmd.filename.endswith('.json') else f"{parsed_cmd.filename}.json"
            new_composition, error = load_project(filename)
            if error:
                return f"Error: {error}"
            self.composition = new_composition
            self.sequencer.stop()
            self.sequencer = Sequencer(self.composition, self.instruments)
            self.update_track_display() # Explicitly update display after loading
            return f"Project {filename} loaded successfully."

        if parsed_cmd.action in ['export', 'render']:
            if not parsed_cmd.filename:
                return "Please specify a filename, e.g., 'export my_song.wav'."
            filename = parsed_cmd.filename if parsed_cmd.filename.endswith('.wav') else f"{parsed_cmd.filename}.wav"
            error = render_composition_to_wav(self.composition, self.instruments, filename)
            return f"Composition exported to {filename}." if not error else f"Error: {error}"

        if parsed_cmd.action in ['delete', 'remove']:
            track_id = parsed_cmd.target_track_id
            if track_id is None:
                return "Please specify which track to delete, e.g., 'delete 0'."
            if 0 <= track_id < len(self.composition.tracks):
                deleted_track = self.composition.tracks.pop(track_id)
                self.sequencer.stop()
                self.sequencer = Sequencer(self.composition, self.instruments)
                return f"OK, I've deleted track {track_id} ({deleted_track.instrument_id})."
            else:
                return f"Track {track_id} not found."
        
        instrument_name = parsed_cmd.instrument
        if not instrument_name:
            return "Sorry, I don't know what instrument to use."

        if instrument_name not in self.instruments:
            return f"I don't have an instrument called '{instrument_name}'. Try: kick, snare, hat."

        # Generate a new pattern
        new_pattern = generate_pattern(parsed_cmd)
        
        # Create a new track for this pattern
        new_track = Track(instrument_id=instrument_name, patterns=[new_pattern])
        self.composition.tracks.append(new_track)
        
        # Re-initialize the sequencer with the updated composition
        self.sequencer.stop()
        self.sequencer = Sequencer(self.composition, self.instruments)

        return f"OK, I've created a new '{instrument_name}' pattern. Press SPACE to play."

class VibeTrackerApp(App):
    """A Textual app for the Vibe Tracker."""

    TITLE = "Vibe Tracker - AI Music Studio"
    SUB_TITLE = "Compose music with natural language"

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("space", "toggle_play", "Play/Pause"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Horizontal(id="app-grid"):
            with Vertical(id="left-pane"):
                yield RichLog(id="log", wrap=True, highlight=True)
                yield Input(placeholder="e.g., 'create a techno kick'", id="command_input")
            with Vertical(id="right-pane"):
                yield Static("No tracks yet.", id="track_display")

    def on_mount(self) -> None:
        self.music_engine = MusicEngine()
        log = self.query_one(RichLog)
        log.write("Welcome! I'm your AI music assistant. Give me a command to start.")
        self.query_one("#command_input").focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value
        log = self.query_one(RichLog)
        log.write(f"> {command}")
        self.query_one(Input).clear()

        response = self.music_engine.process_command(command)
        log.write(f"AI: {response}")
        self.update_track_display()

    def action_toggle_play(self) -> None:
        """Toggle music playback."""
        log = self.query_one(RichLog)
        if self.music_engine.sequencer.is_playing:
            self.music_engine.sequencer.stop()
            log.write("Playback stopped.")
        else:
            if not self.music_engine.composition.tracks:
                log.write("There's nothing to play yet! Create a track first.")
                return
            self.music_engine.sequencer.play()
            log.write("Playback started...")

    def update_track_display(self) -> None:
        """Updates the track display widget with the current list of tracks."""
        track_display = self.query_one("#track_display", Static)
        tracks = self.music_engine.composition.tracks
        if not tracks:
            track_display.update("No tracks yet.")
            return

        display_text = "[b]Current Tracks:[/b]\n\n"
        for i, track in enumerate(tracks):
            display_text += f"- Track {i}: {track.instrument_id}\n"
        
        track_display.update(display_text)

    def action_quit(self) -> None:
        """Cleanly exit the application."""
        self.music_engine.sequencer.stop()
        self.exit()

if __name__ == "__main__":
    app = VibeTrackerApp()
    app.run()
