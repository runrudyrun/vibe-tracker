from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Input, RichLog, Static
import logging
import json
from textual.worker import Worker
from textual import events

# --- Project Imports ---
from .music_structures import Composition, Track, Pattern, NoteEvent
from .sequencer import Sequencer
from .synthesis import Instrument, get_waveform_function, WAVEFORM_MAP, SAMPLE_RATE
from .llm_generator import LLMGenerator
from .exporter import save_composition_to_json, render_composition_to_wav
from .track_display import TrackDisplayWidget, PlaybackVisualizationWidget

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
        if not self.composition:
            return None # Return None if there's no composition

        # Use the built-in to_dict methods for a consistent and reliable serialization
        composition_dict = self.composition.to_dict()
        composition_dict['instruments'] = [inst.to_dict() for inst in self.instruments.values()]
        
        return composition_dict

    def update_composition_from_llm(self, music_data: dict) -> str:
        """Updates the current composition based on data from the LLM."""
        if not music_data or 'tracks' not in music_data:
            return "AI returned empty or invalid data."

        try:
            # Use the robust from_dict methods to create the new composition and instruments
            new_composition = Composition.from_dict(music_data)
            new_instruments = {
                inst_data['name']: Instrument.from_dict(inst_data)
                for inst_data in music_data.get('instruments', [])
            }

            # --- Log the structure of the new composition for debugging purposes ---
            self.logger.info("--- New Composition Received from LLM ---")
            self.logger.info(f"BPM: {new_composition.bpm}")
            for i, track in enumerate(new_composition.tracks):
                self.logger.info(f"  Track {i} (ID: {track.instrument_id}):")
                self.logger.info(f"    Patterns: {len(track.patterns)}")
                self.logger.info(f"    Sequence: {track.sequence}")
                for j, pattern in enumerate(track.patterns):
                    # Represent note and its duration
                    step_summary = []
                    for s in pattern.steps:
                        if s and s.note:
                            if s.duration > 1:
                                step_summary.append(f"N({s.duration})")
                            else:
                                step_summary.append("N")
                        else:
                            step_summary.append("_")
                    self.logger.info(f"      Pattern {j}: Steps: {len(pattern.steps)}")
                    self.logger.info(f"      Pattern {j} Content: {''.join(step_summary)}")
            self.logger.info("-----------------------------------------")

            # Atomically update the MusicEngine's and the sequencer's state
            self.composition = new_composition
            self.instruments.update(new_instruments)
            self.sequencer.update_composition(self.composition, self.instruments)

            track_count = len(new_composition.tracks)
            return f"Composition updated: {track_count} tracks, BPM: {new_composition.bpm}."

        except Exception as e:
            self.logger.error(f"Failed to update composition: {e}", exc_info=True)
            return f"Error processing AI response: {e}"

class VibeTrackerApp(App):
    """A Textual app for the Vibe Tracker."""

    TITLE = "Vibe Tracker - AI Music Studio"
    SUB_TITLE = "Compose music with natural language | SPACE: Play/Pause | Ctrl-S: Save JSON | Ctrl-E: Export WAV | Ctrl-Q: Quit"

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("space", "toggle_play", "Play/Pause"),
        ("ctrl+s", "save_json", "Save JSON"),
        ("ctrl+e", "export_wav", "Export WAV"),
    ]

    def __init__(self):
        super().__init__()
        self.music_engine = MusicEngine(logger=logging.getLogger(__name__))
        self.input_mode = 'prompt'  # 'prompt', 'save_json', 'export_wav'
        
        # Initialize widgets
        self.input_widget = Input(placeholder="Enter a prompt for the AI...", id="command_input")
        self.log_widget = RichLog(wrap=True, highlight=True, markup=True)
        self.track_display_widget = TrackDisplayWidget(id="track_display")
        self.playback_widget = PlaybackVisualizationWidget(id="playback_display")
        
        # Timer for periodic display updates during playback
        self.update_timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            # Playback visualization at the top
            yield self.playback_widget
            with Horizontal(id="main_container"):
                yield self.log_widget
                with Vertical(id="right_panel"):
                    yield self.track_display_widget
            yield self.input_widget
        yield Footer()

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
        self.log_widget.write("Welcome! I'm your AI music assistant. Give me a command to start.")
        self.query_one("#command_input").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value
        self.input_widget.clear()
        if self.input_mode == 'prompt':
            self.log_widget.write(f"> {value}")
            self.log_widget.write("AI: Thinking... (this might take a moment)")
            self.run_worker(self.generate_music(value), exclusive=True)
        elif self.input_mode == 'save_json':
            self.run_worker(self.worker_save_json(value))
            self.set_input_mode('prompt')
        elif self.input_mode == 'export_wav':
            self.run_worker(self.worker_export_wav(value))
            self.set_input_mode('prompt')

    def set_input_mode(self, mode: str, prompt_text: str = "Enter a prompt..."):
        self.input_mode = mode
        self.input_widget.placeholder = prompt_text
        self.input_widget.focus()

    async def generate_music(self, prompt: str) -> None:
        """Worker function to call the LLM and process the response, now context-aware and non-blocking."""
        # 1. Get the current state of the music as a dictionary.
        current_composition_dict = self.music_engine.get_composition_as_dict()

        # Log the context being sent to the LLM
        if current_composition_dict:
            self.logger.info(f"\n--- CONTEXT SENT TO LLM ---\n{json.dumps(current_composition_dict, indent=2)}\n---------------------------")
        else:
            self.logger.info("--- CONTEXT SENT TO LLM: Empty composition ---")

        # 2. Call the LLM with the user prompt and the current composition as context.
        music_data, error = self.music_engine.llm_generator.generate_music_from_prompt(
            prompt,
            context_composition=current_composition_dict
        )

        # 3. Process the response.
        if error:
            self.log_widget.write(f"AI: Sorry, an error occurred: {error}")
            self.logger.error(f"LLM Error: {error}")
        else:
            # Log the data received from the LLM
            self.logger.info(f"\n--- DATA RECEIVED FROM LLM ---\n{json.dumps(music_data, indent=2)}\n------------------------------")
            
            # The `update_composition_from_llm` method will atomically update the live sequencer.
            response_message = self.music_engine.update_composition_from_llm(music_data)
            self.log_widget.write(f"AI: {response_message}")
            self.update_track_display()

    def action_toggle_play(self) -> None:
        """Toggle music playback."""
        if self.music_engine.sequencer.is_playing:
            self.music_engine.sequencer.stop()
            self.log_widget.write("Playback stopped.")
            # Stop periodic updates
            if self.update_timer:
                self.update_timer.stop()
                self.update_timer = None
        else:
            if not self.music_engine.composition.tracks:
                self.log_widget.write("There's nothing to play yet! Create a track first.")
                return
            self.music_engine.sequencer.play()
            self.log_widget.write("Playback started...")
            # Start periodic updates (reduced frequency to avoid audio issues)
            self.update_timer = self.set_interval(0.25, self.update_track_display)  # Update 4 times per second
        
        # Update display immediately
        self.update_track_display()

    def action_save_json(self) -> None:
        if not self.music_engine.composition.tracks:
            self.log_widget.write("Cannot save an empty composition.")
            return
        self.set_input_mode('save_json', "Enter filename for JSON (e.g., 'my_song.json'):")

    async def worker_save_json(self, filepath: str):
        self.log_widget.write(f"Saving to {filepath}...")
        error = save_composition_to_json(
            self.music_engine.composition, self.music_engine.instruments, filepath
        )
        if error:
            self.log_widget.write(f"[bold red]Error saving JSON:[/] {error}")
        else:
            self.log_widget.write(f"[bold green]Successfully saved to {filepath}[/]")

    def action_export_wav(self) -> None:
        if not self.music_engine.composition.tracks:
            self.log_widget.write("Cannot export an empty composition.")
            return
        self.set_input_mode('export_wav', "Enter filename for WAV (e.g., 'my_song.wav'):")

    async def worker_export_wav(self, filepath: str):
        self.log_widget.write(f"Rendering to {filepath}... (this may take a moment)")
        error = render_composition_to_wav(
            self.music_engine.composition, self.music_engine.instruments, filepath
        )
        if error:
            self.log_widget.write(f"[bold red]Error exporting WAV:[/] {error}")
        else:
            self.log_widget.write(f"[bold green]Successfully exported to {filepath}[/]")

    def update_track_display(self) -> None:
        """Updates the track display widget with the current list of tracks."""
        # Get current playback position from sequencer
        current_step = getattr(self.music_engine.sequencer, '_current_frame', 0)
        if hasattr(self.music_engine.sequencer, 'composition') and self.music_engine.sequencer.composition:
            step_duration_frames = int(self.music_engine.sequencer.composition.get_step_duration() * SAMPLE_RATE)
            if step_duration_frames > 0:
                current_step = current_step // step_duration_frames
        else:
            current_step = 0
            
        # Update enhanced track display
        self.track_display_widget.update_tracks(
            self.music_engine.composition, 
            self.music_engine.instruments, 
            current_step
        )
        
        # Update playback visualization with fixed loop length
        total_steps = 64  # Standard pattern length
        
        self.playback_widget.update_playback(
            current_step,
            total_steps,
            self.music_engine.composition.bpm,
            self.music_engine.sequencer.is_playing
        )

    def action_quit(self) -> None:
        """Cleanly exit the application."""
        # Stop timer if running
        if self.update_timer:
            self.update_timer.stop()
            self.update_timer = None
        self.music_engine.sequencer.stop()
        self.exit()

if __name__ == "__main__":
    app = VibeTrackerApp()
    app.run()
