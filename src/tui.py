from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Input, RichLog, Static, Button
from textual.screen import ModalScreen
import logging
import json
import os
from pathlib import Path
from textual.worker import Worker

# --- Project Imports ---
from .music_structures import Composition, Track, Pattern, NoteEvent
from .sequencer import Sequencer
from .synthesis import Instrument, get_waveform_function, WAVEFORM_MAP
from .llm_generator import LLMGenerator
from .exporter import save_composition_to_json, render_composition_to_wav
from .pattern_manager import PatternManager

class RawResponseModal(ModalScreen):
    """Modal screen to display raw AI responses and parsing details."""
    
    def __init__(self, raw_response: str, parsed_data: dict = None, error: str = None):
        super().__init__()
        self.raw_response = raw_response
        self.parsed_data = parsed_data
        self.error = error
    
    def compose(self) -> ComposeResult:
        with Vertical(id="raw_response_modal"):
            yield Static("[bold]Raw AI Response:[/bold]", classes="modal-title")
            yield RichLog(wrap=True, highlight=True, markup=True, id="raw_log")
            if self.error:
                yield Static(f"[bold red]Parsing Error:[/bold red] {self.error}", classes="error-text")
            yield Button("Close", variant="primary", id="close_modal")
    
    def on_mount(self) -> None:
        raw_log = self.query_one("#raw_log", RichLog)
        raw_log.write("[bold cyan]Raw Response:[/bold cyan]")
        raw_log.write(self.raw_response)
        
        if self.parsed_data:
            raw_log.write("\n[bold green]Parsed JSON:[/bold green]")
            raw_log.write(json.dumps(self.parsed_data, indent=2))
        
        if self.error:
            raw_log.write(f"\n[bold red]Error Details:[/bold red]")
            raw_log.write(self.error)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_modal":
            self.dismiss()

class MusicEngine:
    """Manages the musical state of the application using an LLM."""
    def __init__(self, logger):
        self.logger = logger
        self.composition = Composition(bpm=120)
        self.instruments = {}
        self.sequencer = Sequencer(self.composition, self.instruments, logger=self.logger)
        self.llm_generator = LLMGenerator()
        self.pattern_manager = PatternManager()

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
    CSS = """
    #raw_response_modal {
        width: 80%;
        height: 80%;
        margin: 2 4;
        padding: 1;
        border: solid $primary;
        background: $surface;
    }
    
    .modal-title {
        text-align: center;
        margin-bottom: 1;
    }
    
    .error-text {
        margin: 1 0;
        padding: 1;
        background: $error 20%;
        border-left: solid red;
    }
    
    #raw_log {
        height: 1fr;
        margin-bottom: 1;
        border: solid $accent;
    }
    
    #close_modal {
        width: 100%;
    }
    """
    """A Textual app for the Vibe Tracker."""

    TITLE = "Vibe Tracker - AI Music Studio"
    SUB_TITLE = "Compose music with natural language | SPACE: Play/Pause | Ctrl-S: Save JSON | Ctrl-E: Export WAV | Ctrl-T: Save Pattern | Ctrl-L: Load Pattern | Ctrl-B: Library | Ctrl-X: Clear Project | Ctrl-D: Delete Track | Ctrl-Q: Quit"

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("space", "toggle_play", "Play/Pause"),
        ("ctrl+s", "save_json", "Save JSON"),
        ("ctrl+e", "export_wav", "Export WAV"),
        ("ctrl+t", "save_pattern", "Save Pattern"),
        ("ctrl+l", "load_pattern", "Load Pattern"),
        ("ctrl+b", "pattern_library", "Pattern Library"),
        ("ctrl+x", "clear_project", "Clear Project"),
        ("ctrl+d", "delete_track", "Delete Track"),
        ("ctrl+r", "toggle_raw_responses", "Toggle Raw Responses"),
    ]

    def __init__(self):
        super().__init__()
        self.input_mode = "prompt"
        self.input_widget = Input(placeholder="Enter a prompt for the AI...", id="command_input")
        self.log_widget = RichLog(wrap=True, highlight=True, markup=True)
        self.track_display = Static("No tracks yet.", id="track_display")
        self.show_raw_responses = False  # Toggle for showing raw responses
        self.last_raw_response = None
        self.last_parsed_data = None
        self.last_parsing_error = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with Horizontal(id="main_container"):
                yield self.log_widget
                with Vertical(id="right_panel"):
                    yield self.track_display
                    yield Button("Show Raw Response", variant="default", id="show_raw_btn", disabled=True)
                    yield Button("Auto-Show: OFF", variant="default", id="toggle_auto_raw")
            yield self.input_widget
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "show_raw_btn":
            if self.last_raw_response:
                self.push_screen(RawResponseModal(
                    self.last_raw_response, 
                    self.last_parsed_data, 
                    self.last_parsing_error
                ))
            else:
                self.log_widget.write("[yellow]No raw response available yet. Generate some music first![/yellow]")
        elif event.button.id == "toggle_auto_raw":
            self.action_toggle_raw_responses()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Load .env file
        self._load_env_file()
        
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
    
    def _load_env_file(self):
        """Load environment variables from .env file"""
        env_file = Path(__file__).parent.parent / '.env'
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value.strip('"\'')
            print(f"[TUI] Loaded .env file with {len([l for l in open(env_file) if '=' in l and not l.startswith('#')])} variables")

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
        elif self.input_mode == 'save_pattern':
            self.run_worker(self.worker_save_pattern(value))
            self.set_input_mode('prompt')
        elif self.input_mode == 'load_pattern':
            self.run_worker(self.worker_load_pattern(value))
            self.set_input_mode('prompt')
        elif self.input_mode == 'save_choice':
            if value.strip() == '1':
                self.set_input_mode('save_pattern', "Enter name for individual patterns:")
            elif value.strip() == '2':
                self.set_input_mode('save_composition', "Enter name for full composition:")
            else:
                self.log_widget.write("Invalid choice. Please enter 1 or 2.")
                self.set_input_mode('save_choice', "Choose save type (1 or 2):")
        elif self.input_mode == 'save_composition':
            self.run_worker(self.worker_save_composition(value))
            self.set_input_mode('prompt')
        elif self.input_mode == 'load_auto':
            self.run_worker(self.worker_load_auto(value))
            self.set_input_mode('prompt')
        elif self.input_mode == 'delete_track':
            self.worker_delete_track(value)
            self.set_input_mode('prompt')

    def set_input_mode(self, mode: str, prompt_text: str = "Enter a prompt..."):
        self.input_mode = mode
        self.input_widget.placeholder = prompt_text
        self.input_widget.focus()

    async def generate_music(self, prompt: str):
        """Worker method to generate music from a prompt."""
        try:
            # Get the current composition as context for the LLM
            current_composition = self.music_engine.get_composition_as_dict()
            
            # Generate new music data using the LLM
            music_data, error, raw_response = self.music_engine.llm_generator.generate_music_from_prompt(
                prompt, current_composition
            )
            
            # Store raw response and parsing results for debugging
            self.last_raw_response = raw_response
            self.last_parsed_data = music_data
            self.last_parsing_error = error
            
            # Update button text based on availability of raw response
            raw_btn = self.query_one("#show_raw_btn", Button)
            if raw_response:
                raw_btn.label = "Show Raw Response" if not error else "Show Raw Response (Error)"
                raw_btn.disabled = False
            else:
                raw_btn.disabled = True
            
            if error:
                self.log_widget.write(f"[bold red]AI Error:[/] {error}")
                if self.show_raw_responses and raw_response:
                    self.push_screen(RawResponseModal(raw_response, music_data, error))
                return
            
            # The `update_composition_from_llm` method will atomically update the live sequencer.
            response_message = self.music_engine.update_composition_from_llm(music_data)
            self.log_widget.write(f"AI: {response_message}")
            
            # Auto-show raw response if enabled
            if self.show_raw_responses and raw_response:
                self.push_screen(RawResponseModal(raw_response, music_data, error))
                
            self.update_track_display()
        except Exception as e:
            self.log_widget.write(f"[bold red]Unexpected error:[/] {str(e)}")
            self.logger.error(f"Generate music error: {e}")
    
    def action_toggle_raw_responses(self) -> None:
        """Toggle automatic showing of raw AI responses."""
        self.show_raw_responses = not self.show_raw_responses
        auto_btn = self.query_one("#toggle_auto_raw", Button)
        
        if self.show_raw_responses:
            auto_btn.label = "Auto-Show: ON"
            auto_btn.variant = "success"
            self.log_widget.write("[green]Raw responses will now auto-show after each generation[/green]")
        else:
            auto_btn.label = "Auto-Show: OFF"
            auto_btn.variant = "default"
            self.log_widget.write("[yellow]Raw responses auto-show disabled[/yellow]")

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

    def action_save_pattern(self) -> None:
        """Save current music to library."""
        if not self.music_engine.composition.tracks:
            self.log_widget.write("No tracks to save.")
            return
            
        # Auto-decide: multiple tracks = composition, single track = pattern
        if len(self.music_engine.composition.tracks) > 1:
            self.log_widget.write(f"Saving composition with {len(self.music_engine.composition.tracks)} tracks...")
            self.set_input_mode('save_composition', "Enter name to save:")
        else:
            self.log_widget.write("Saving single track pattern...")
            self.set_input_mode('save_pattern', "Enter name to save:")

    def action_load_pattern(self) -> None:
        """Load music from library."""
        items = self.music_engine.pattern_manager.list_all_items()
        if not items:
            self.log_widget.write("Library is empty. Use Ctrl+T to save music first.")
            return
            
        self.log_widget.write("Available items to load:")
        for item in items[:5]:  # Show first 5 items
            if item['type'] == 'composition':
                self.log_widget.write(f"• {item['name']} (composition, {item['tracks']} tracks)")
            else:
                self.log_widget.write(f"• {item['name']} (pattern, {item.get('instrument_id', 'unknown')})")
        if len(items) > 5:
            self.log_widget.write(f"... and {len(items) - 5} more (use Ctrl+B to see all)")
            
        self.set_input_mode('load_auto', "Enter name to load:")

    def action_pattern_library(self) -> None:
        """Show pattern and composition library browser."""
        items = self.music_engine.pattern_manager.list_all_items()
        if not items:
            self.log_widget.write("Library is empty. Use Ctrl+T to save patterns or compositions.")
            return
            
        self.log_widget.write("[bold]Pattern & Composition Library:[/bold]")
        
        # Group by type for better display
        patterns = [item for item in items if item['type'] == 'pattern']
        compositions = [item for item in items if item['type'] == 'composition']
        
        if compositions:
            self.log_widget.write("\n[bold cyan]🎵 Compositions:[/bold cyan]")
            for comp in compositions:
                tags_str = ", ".join(comp['tags']) if comp['tags'] else "No tags"
                self.log_widget.write(
                    f"• {comp['name']} ({comp['tracks']} tracks, {comp['bpm']} BPM) - {tags_str} - {comp['created_at'][:10]}"
                )
        
        if patterns:
            self.log_widget.write("\n[bold green]🎼 Individual Patterns:[/bold green]")
            for pattern in patterns:
                tags_str = ", ".join(pattern['tags']) if pattern['tags'] else "No tags"
                instrument = pattern.get('instrument_id', 'unknown')
                self.log_widget.write(
                    f"• {pattern['name']} ({pattern['steps']} steps, {instrument}) - {tags_str} - {pattern['created_at'][:10]}"
                )
        
        self.log_widget.write("\nUse Ctrl+L to load a pattern or composition.")

    async def worker_save_pattern(self, pattern_name: str):
        """Worker to save all patterns from all tracks to library."""
        if not self.music_engine.composition.tracks:
            self.log_widget.write("No tracks available to save patterns from.")
            return
        
        saved_count = 0
        failed_count = 0
        
        # Save patterns from all tracks
        for track_idx, track in enumerate(self.music_engine.composition.tracks):
            if not track.patterns:
                self.log_widget.write(f"Track {track_idx} ({track.instrument_id}) has no patterns, skipping.")
                continue
                
            # Save the first pattern from each track
            pattern = track.patterns[0]
            instrument_id = track.instrument_id
            
            # Create unique name for each track's pattern
            if len(self.music_engine.composition.tracks) > 1:
                track_pattern_name = f"{pattern_name}_{instrument_id}"
            else:
                track_pattern_name = pattern_name
            
            # Generate tags based on instrument and pattern characteristics
            tags = []
            if instrument_id:
                tags.append(instrument_id.replace('_', ' '))
            
            # Count active steps for additional tag info
            active_steps = sum(1 for step in pattern.steps if step and step.note)
            if active_steps <= 4:
                tags.append("sparse")
            elif active_steps >= 12:
                tags.append("dense")
            else:
                tags.append("medium")
            
            # Add multi-track tag if applicable
            if len(self.music_engine.composition.tracks) > 1:
                tags.append("multi-track")
                
            success = self.music_engine.pattern_manager.save_pattern(
                pattern, track_pattern_name, tags=tags, instrument_id=instrument_id
            )
            
            if success:
                saved_count += 1
                tags_str = ", ".join(tags) if tags else "no tags"
                self.log_widget.write(f"✓ Saved '{track_pattern_name}' with tags: {tags_str}")
            else:
                failed_count += 1
                self.log_widget.write(f"✗ Failed to save '{track_pattern_name}'")
        
        # Summary message
        if saved_count > 0:
            self.log_widget.write(f"[bold green]Successfully saved {saved_count} pattern(s)![/bold green]")
        if failed_count > 0:
            self.log_widget.write(f"[bold red]Failed to save {failed_count} pattern(s)[/bold red]")

    async def worker_load_pattern(self, pattern_name: str):
        """Worker to load pattern from library."""
        result = self.music_engine.pattern_manager.load_pattern(pattern_name)
        
        if not result:
            self.log_widget.write(f"[bold red]Pattern '{pattern_name}' not found[/bold red]")
            return
            
        pattern, metadata = result
        instrument_id = metadata.get('instrument_id', 'default')
        
        # Create a new track with the loaded pattern
        from .music_structures import Track
        new_track = Track(instrument_id=instrument_id)
        new_track.patterns = [pattern]
        new_track.sequence = [0]  # Play the loaded pattern
        
        # Ensure the instrument exists - create a default one if needed
        if instrument_id not in self.music_engine.instruments:
            from .synthesis import Instrument
            # Create a default instrument for the loaded pattern
            default_instrument = Instrument(
                name=instrument_id,
                oscillators=[{'waveform': 'sine', 'amplitude': 0.7}],
                attack=0.01,
                decay=0.1,
                sustain_level=0.7,
                release=0.2
            )
            self.music_engine.instruments[instrument_id] = default_instrument
            self.log_widget.write(f"Created default instrument for '{instrument_id}'")
        
        # Add to composition
        self.music_engine.composition.tracks.append(new_track)
        
        # Update sequencer
        self.music_engine.sequencer.update_composition(
            self.music_engine.composition, self.music_engine.instruments
        )
        
        self.log_widget.write(f"[bold green]Pattern '{pattern_name}' loaded successfully![/bold green]")
        self.update_track_display()

    async def worker_load_auto(self, name: str):
        """Universal worker to load any type of music (pattern or composition)."""
        # First try to load as composition
        comp_result = self.music_engine.pattern_manager.load_composition(name)
        if comp_result:
            composition, instruments, metadata = comp_result
            
            # Replace current composition entirely
            self.music_engine.composition = composition
            self.music_engine.instruments = instruments
            
            # Update sequencer
            self.music_engine.sequencer.update_composition(
                self.music_engine.composition, self.music_engine.instruments
            )
            
            track_count = len(composition.tracks)
            self.log_widget.write(f"[bold green]Composition '{name}' loaded successfully![/bold green]")
            self.log_widget.write(f"Loaded {track_count} tracks with {len(instruments)} instruments")
            self.update_track_display()
            return
        
        # If not a composition, try to load as pattern
        pattern_result = self.music_engine.pattern_manager.load_pattern(name)
        if pattern_result:
            pattern, metadata = pattern_result
            instrument_id = metadata.get('instrument_id', 'default')
            
            # Create a new track with the loaded pattern
            from .music_structures import Track
            new_track = Track(instrument_id=instrument_id)
            new_track.patterns = [pattern]
            new_track.sequence = [0]
            
            # Ensure the instrument exists
            if instrument_id not in self.music_engine.instruments:
                from .synthesis import Instrument
                default_instrument = Instrument(
                    name=instrument_id,
                    oscillators=[{'waveform': 'sine', 'amplitude': 0.7}],
                    attack=0.01,
                    decay=0.1,
                    sustain_level=0.7,
                    release=0.2
                )
                self.music_engine.instruments[instrument_id] = default_instrument
                self.log_widget.write(f"Created default instrument for '{instrument_id}'")
            
            # Add to composition
            self.music_engine.composition.tracks.append(new_track)
            
            # Update sequencer
            self.music_engine.sequencer.update_composition(
                self.music_engine.composition, self.music_engine.instruments
            )
            
            self.log_widget.write(f"[bold green]Pattern '{name}' loaded successfully![/bold green]")
            self.update_track_display()
            return
        
        # Nothing found
        self.log_widget.write(f"[bold red]'{name}' not found in library[/bold red]")

    async def worker_save_composition(self, composition_name: str):
        """Worker to save full composition to library."""
        if not self.music_engine.composition.tracks:
            self.log_widget.write("No tracks available to save composition from.")
            return
        
        # Generate tags for the composition
        tags = []
        track_count = len(self.music_engine.composition.tracks)
        tags.append(f"{track_count}-track")
        
        # Add instrument types as tags
        instrument_types = set()
        for track in self.music_engine.composition.tracks:
            if track.instrument_id:
                instrument_types.add(track.instrument_id.replace('_', ' '))
        tags.extend(list(instrument_types))
        
        # Add BPM info
        tags.append(f"bpm-{self.music_engine.composition.bpm}")
        
        success = self.music_engine.pattern_manager.save_composition(
            self.music_engine.composition, 
            self.music_engine.instruments, 
            composition_name, 
            tags=tags
        )
        
        if success:
            tags_str = ", ".join(tags) if tags else "no tags"
            self.log_widget.write(f"[bold green]Composition '{composition_name}' saved with {track_count} tracks![/bold green]")
            self.log_widget.write(f"Tags: {tags_str}")
        else:
            self.log_widget.write(f"[bold red]Failed to save composition '{composition_name}'[/bold red]")

    async def worker_load_composition(self, composition_name: str):
        """Worker to load full composition from library."""
        result = self.music_engine.pattern_manager.load_composition(composition_name)
        
        if not result:
            self.log_widget.write(f"[bold red]Composition '{composition_name}' not found[/bold red]")
            return
            
        composition, instruments, metadata = result
        
        # Replace current composition entirely
        self.music_engine.composition = composition
        self.music_engine.instruments = instruments
        
        # Update sequencer
        self.music_engine.sequencer.update_composition(
            self.music_engine.composition, self.music_engine.instruments
        )
        
        track_count = len(composition.tracks)
        self.log_widget.write(f"[bold green]Composition '{composition_name}' loaded successfully![/bold green]")
        self.log_widget.write(f"Loaded {track_count} tracks with {len(instruments)} instruments")
        self.update_track_display()

    def action_clear_project(self) -> None:
        """Clear the entire project (all tracks and instruments)."""
        if not self.music_engine.composition.tracks:
            self.log_widget.write("[yellow]Project is already empty.[/yellow]")
            return
        
        # Stop playback first
        self.music_engine.sequencer.stop()
        
        # Clear all tracks and instruments
        track_count = len(self.music_engine.composition.tracks)
        self.music_engine.composition.tracks.clear()
        self.music_engine.instruments.clear()
        
        # Update sequencer with empty composition
        self.music_engine.sequencer.update_composition(
            self.music_engine.composition, self.music_engine.instruments
        )
        
        # Update display
        self.update_track_display()
        
        self.log_widget.write(f"[bold green]Project cleared! Removed {track_count} tracks.[/bold green]")

    def action_delete_track(self) -> None:
        """Delete a specific track by prompting for track number."""
        if not self.music_engine.composition.tracks:
            self.log_widget.write("[yellow]No tracks to delete.[/yellow]")
            return
        
        # Show current tracks
        self.log_widget.write("[bold]Current tracks:[/bold]")
        for i, track in enumerate(self.music_engine.composition.tracks):
            self.log_widget.write(f"  {i}: {track.instrument_id}")
        
        # Set input mode to get track number
        self.set_input_mode("delete_track", "Enter track number to delete (0-based):")

    def worker_delete_track(self, track_input: str) -> None:
        """Worker to delete a specific track by index."""
        try:
            track_index = int(track_input.strip())
        except ValueError:
            self.log_widget.write("[bold red]Invalid input. Please enter a number.[/bold red]")
            return
        
        if track_index < 0 or track_index >= len(self.music_engine.composition.tracks):
            self.log_widget.write(f"[bold red]Invalid track index. Please enter 0-{len(self.music_engine.composition.tracks)-1}.[/bold red]")
            return
        
        # Stop playback first
        self.music_engine.sequencer.stop()
        
        # Get track info before deletion
        deleted_track = self.music_engine.composition.tracks[track_index]
        instrument_id = deleted_track.instrument_id
        
        # Remove the track
        self.music_engine.composition.tracks.pop(track_index)
        
        # Remove instrument if no other tracks use it
        instrument_still_used = any(
            track.instrument_id == instrument_id 
            for track in self.music_engine.composition.tracks
        )
        if not instrument_still_used and instrument_id in self.music_engine.instruments:
            del self.music_engine.instruments[instrument_id]
        
        # Update sequencer
        self.music_engine.sequencer.update_composition(
            self.music_engine.composition, self.music_engine.instruments
        )
        
        # Update display
        self.update_track_display()
        
        self.log_widget.write(f"[bold green]Track {track_index} ({instrument_id}) deleted successfully![/bold green]")

    def action_quit(self) -> None:
        """Cleanly exit the application."""
        self.music_engine.sequencer.stop()
        self.exit()

if __name__ == "__main__":
    app = VibeTrackerApp()
    app.run()
