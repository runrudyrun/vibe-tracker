from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Input, RichLog, Static
from textual.worker import Worker

# --- Project Imports ---
from .music_structures import Composition, Track, Pattern
from .sequencer import Sequencer
from .synthesis import Instrument, get_waveform_function, WAVEFORM_MAP
from .llm_generator import LLMGenerator


class MusicEngine:
    """Manages the musical state of the application using an LLM."""
    def __init__(self, app_ref):
        self.app = app_ref
        self.composition = Composition(bpm=120)
        self.instruments = {}
        self.sequencer = Sequencer(self.composition, self.instruments)
        self.llm_generator = LLMGenerator()

    def get_composition_as_dict(self):
        """Serializes the current composition and instruments into a dictionary for the LLM."""
        if not self.composition or not self.composition.tracks:
            return None

        # Create a reverse map from function object to its string name
        waveform_name_map = {v: k for k, v in WAVEFORM_MAP.items()}

        return {
            "bpm": self.composition.bpm,
            "instruments": [
                {
                    "name": name,
                    "waveform": waveform_name_map.get(inst.waveform_func, 'sine'),
                    "attack": inst.attack,
                    "decay": inst.decay,
                    "sustain_level": inst.sustain_level,
                    "release": inst.release
                } for name, inst in self.instruments.items()
            ],
            "tracks": [
                {
                    "instrument_name": track.instrument_id,
                    "notes": [
                        {"step": step_index, "note": note_event.note}
                        for pattern in track.patterns
                        for step_index, note_event in enumerate(pattern.steps)
                        if note_event and note_event.note is not None
                    ]
                } for track in self.composition.tracks
            ]
        }

    def update_composition_from_llm(self, music_data):
        """Rebuilds the composition from LLM data and updates the sequencer."""
        try:
            # Create a new composition object from the data
            new_composition = Composition(bpm=music_data.get('bpm', 120))
            new_instruments = {}

            for inst_data in music_data.get('instruments', []):
                name = inst_data['name']
                waveform_func = get_waveform_function(inst_data['waveform'])
                new_instruments[name] = Instrument(
                    waveform_func=waveform_func,
                    attack=float(inst_data['attack']),
                    decay=float(inst_data['decay']),
                    sustain_level=float(inst_data['sustain_level']),
                    release=float(inst_data['release'])
                )

            for track_data in music_data.get('tracks', []):
                instrument_name = track_data['instrument_name']
                if instrument_name not in new_instruments:
                    continue
                
                new_pattern = Pattern()
                for note_data in track_data.get('notes', []):
                    new_pattern.set_note(int(note_data['step']), note_data['note'])
                
                new_track = Track(instrument_id=instrument_name, patterns=[new_pattern])
                new_composition.tracks.append(new_track)

            # Atomically update the sequencer with the new composition
            self.sequencer.update_composition(new_composition, new_instruments)
            
            # Also update the engine's direct references for UI updates
            self.composition = new_composition
            self.instruments = new_instruments

            return "OK, I've created a new composition. Press SPACE to play."
        except (KeyError, TypeError, ValueError) as e:
            return f"Sorry, the AI returned data in a format I don't understand. Error: {e}"

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
                yield RichLog(id="log", wrap=True, highlight=True, min_width=60)
                yield Input(placeholder="e.g., 'a funky bassline with a slow disco beat'", id="command_input")
            with Vertical(id="right-pane"):
                yield Static("No tracks yet.", id="track_display")

    def on_mount(self) -> None:
        self.music_engine = MusicEngine(self)
        self.log_widget = self.query_one(RichLog)
        self.log_widget.write("Welcome! I'm your AI music assistant. Give me a command to start.")
        self.query_one("#command_input").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value
        self.log_widget.write(f"> {command}")
        self.query_one(Input).clear()
        self.log_widget.write("AI: Thinking... (this might take a moment)")
        self.run_worker(self.generate_music(command), exclusive=True)

    async def generate_music(self, prompt: str) -> None:
        """Worker function to call the LLM and process the response, now context-aware and non-blocking."""
        # 1. Get the current state of the music as a dictionary.
        current_composition_dict = self.music_engine.get_composition_as_dict()

        # 2. Call the LLM with the user prompt and the current composition as context.
        music_data, error = self.music_engine.llm_generator.generate_music_from_prompt(
            prompt,
            context_composition=current_composition_dict
        )

        # 3. Process the response.
        if error:
            self.log_widget.write(f"AI: Sorry, an error occurred: {error}")
        else:
            # The `update_composition_from_llm` method will atomically update the live sequencer.
            response_message = self.music_engine.update_composition_from_llm(music_data)
            self.log_widget.write(f"AI: {response_message}")
            self.update_track_display()

    def action_toggle_play(self) -> None:
        """Toggle music playback."""
        if self.music_engine.sequencer.is_playing:
            self.music_engine.sequencer.stop()
            self.log_widget.write("Playback stopped.")
        else:
            if not self.music_engine.composition.tracks:
                self.log_widget.write("There's nothing to play yet! Create a track first.")
                return
            self.music_engine.sequencer.play()
            self.log_widget.write("Playback started...")

    def update_track_display(self) -> None:
        """Updates the track display widget with the current list of tracks."""
        track_display = self.query_one("#track_display", Static)
        tracks = self.music_engine.composition.tracks
        if not tracks:
            track_display.update("No tracks yet.")
            return

        display_text = "[b]Current Composition:[/b]\n\n"
        display_text += f"[b]BPM:[/b] {self.music_engine.composition.bpm}\n\n"
        display_text += "[b]Tracks:[/b]\n"
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
