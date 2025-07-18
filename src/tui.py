from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Input, RichLog, Static
import logging
from textual.worker import Worker

# --- Project Imports ---
from .music_structures import Composition, Track, Pattern, NoteEvent
from .sequencer import Sequencer
from .synthesis import Instrument, get_waveform_function, WAVEFORM_MAP
from .llm_generator import LLMGenerator


class MusicEngine:
    """Manages the musical state of the application using an LLM."""
    def __init__(self, logger):
        self.logger = logger
        self.composition = Composition(bpm=120)
        self.instruments = {}
        self.sequencer = Sequencer(self.composition, self.instruments, logger=self.logger)
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
                instrument_name = track_data.get('instrument_name')
                if not instrument_name or instrument_name not in new_instruments:
                    continue

                # --- Final Fix: Smart-trimming pattern silence ---
                notes_data = track_data.get('notes', [])
                if not notes_data:
                    steps = [None] # Keep track alive with one step of silence
                else:
                    # First, build the full pattern, potentially with lots of silence
                    max_step = max([d.get('step', 0) for d in notes_data])
                    steps = [None] * (max_step + 1)
                    for note_data in notes_data:
                        step = note_data.get('step')
                        note = note_data.get('note')
                        if step is not None and note is not None:
                            # Create the NoteEvent with only the valid arguments
                            event_data = {'note': note_data.get('note'), 'velocity': note_data.get('velocity', 1.0)}
                            steps[step] = NoteEvent.from_dict(event_data)

                    # Now, find the first and last notes to trim silence
                    first_note_idx = -1
                    last_note_idx = -1
                    for i, step_event in enumerate(steps):
                        if step_event and step_event.note:
                            if first_note_idx == -1:
                                first_note_idx = i
                            last_note_idx = i
                    
                    # Slice the pattern to the actual content
                    if first_note_idx != -1:
                        steps = steps[first_note_idx : last_note_idx + 1]
                    else:
                        steps = [None] # Should not happen if notes_data is not empty, but as a safeguard

                new_pattern = Pattern(steps=steps)
                new_track = Track(instrument_id=instrument_name, patterns=[new_pattern], sequence=[0])
                new_composition.tracks.append(new_track)

            # --- Log the structure of the new composition for debugging purposes ---
            self.logger.info("--- New Composition Received from LLM ---")
            self.logger.info(f"BPM: {new_composition.bpm}")
            for i, track in enumerate(new_composition.tracks):
                self.logger.info(f"  Track {i} (ID: {track.instrument_id}):")
                self.logger.info(f"    Patterns: {len(track.patterns)}")
                self.logger.info(f"    Sequence: {track.sequence}")
                for j, pattern in enumerate(track.patterns):
                    step_summary = ''.join(['N' if s and s.note else '_' for s in pattern.steps])
                    self.logger.info(f"      Pattern {j}: Steps: {len(pattern.steps)}")
                    self.logger.info(f"      Pattern {j} Content: {step_summary}")
            self.logger.info("-----------------------------------------")

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
        # --- Setup Logging ---
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler("vibe_tracker.log", mode='w')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Application starting up...")

        self.music_engine = MusicEngine(self.logger)
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
