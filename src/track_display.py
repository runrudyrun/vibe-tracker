"""
Enhanced track display module for Vibe Tracker.
Provides visual representation of tracks with notation lanes, instrument info, and playback visualization.
"""

from textual.widgets import Static
from textual.containers import Vertical, Horizontal
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from typing import List, Optional, Dict
import math

from .music_structures import Composition, Track, Pattern, NoteEvent, STEPS_PER_PATTERN
from .synthesis import Instrument


class TrackDisplayWidget(Static):
    """Enhanced widget for displaying tracks with notation lanes and instrument info."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_step = 0  # For playback visualization
        self.steps_per_bar = 16  # Display 16 steps per bar
        
    def update_tracks(self, composition: Composition, instruments: Dict[str, Instrument], current_step: int = 0):
        """Update the display with current composition and playback position."""
        self.current_step = current_step
        
        if not composition.tracks:
            self.update("[dim]No tracks yet. Create some music![/dim]")
            return
        
        # Use fixed loop length for consistency with sequencer
        total_loop_steps = 64  # Standard pattern length
        
        # Create compact display
        display_lines = []
        
        # Compact header
        header = f"♪ BPM: {composition.bpm} | Tracks: {len(composition.tracks)} | Loop: {total_loop_steps} steps"
        display_lines.append(f"[bold cyan]{header}[/bold cyan]")
        display_lines.append("")
        
        # Display each track compactly
        for track_idx, track in enumerate(composition.tracks):
            track_lines = self._render_track_compact(track, instruments.get(track.instrument_id), track_idx, total_loop_steps)
            display_lines.extend(track_lines)
            display_lines.append("")  # Add spacing between tracks
        
        self.update("\n".join(display_lines))
    
    def _render_track(self, track: Track, instrument: Optional[Instrument], track_idx: int, total_loop_steps: int) -> Panel:
        """Render a single track with notation lane and instrument info."""
        
        # Track header
        track_title = f"Track {track_idx + 1}: {track.instrument_id}"
        if instrument:
            # Add instrument type info
            waveforms = [osc.get('waveform', 'sine') for osc in instrument.oscillators]
            track_title += f" ({', '.join(waveforms)})"
        
        # Create notation lane
        notation_lane = self._create_notation_lane(track, total_loop_steps)
        
        # Create instrument info panel
        instrument_info = self._create_instrument_info(instrument) if instrument else "[dim]No instrument data[/dim]"
        
        # Combine notation and instrument info
        track_layout = Table.grid(padding=(0, 2))
        track_layout.add_column("notation", ratio=3)
        track_layout.add_column("instrument", ratio=1)
        track_layout.add_row(notation_lane, instrument_info)
        
        return Panel(track_layout, title=track_title, border_style="green")
    
    def _render_track_compact(self, track: Track, instrument: Optional[Instrument], track_idx: int, total_loop_steps: int) -> List[str]:
        """Render a single track in compact format."""
        lines = []
        
        # Track header
        track_title = f"[bold green]Track {track_idx + 1}: {track.instrument_id}[/bold green]"
        if instrument:
            waveforms = [osc.get('waveform', 'sine') for osc in instrument.oscillators]
            track_title += f" [dim]({', '.join(waveforms)})[/dim]"
        lines.append(track_title)
        
        # Compact notation (show only first 32 steps to fit width)
        if track.patterns:
            pattern = track.patterns[0]
            steps_to_show = min(32, len(pattern.steps), total_loop_steps)
            
            # Create compact note line
            note_symbols = []
            for step in range(steps_to_show):
                note_event = pattern.steps[step]
                if note_event and note_event.note:
                    # Use note symbol with velocity indicator
                    if step == self.current_step % total_loop_steps:
                        note_symbols.append("[bold red on white]█[/bold red on white]")
                    else:
                        velocity_symbol = self._velocity_to_symbol(note_event.velocity)
                        note_symbols.append(f"[yellow]{velocity_symbol}[/yellow]")
                else:
                    if step == self.current_step % total_loop_steps:
                        note_symbols.append("[bold red on white]·[/bold red on white]")
                    else:
                        note_symbols.append("[dim]·[/dim]")
            
            # Add bar markers every 4 steps
            display_line = ""
            for i, symbol in enumerate(note_symbols):
                if i > 0 and i % 4 == 0:
                    display_line += "|"
                display_line += symbol
            
            lines.append(f"  {display_line}")
            
            # Add instrument info
            if instrument:
                adsr_info = f"A:{instrument.attack:.1f} D:{instrument.decay:.1f} S:{instrument.sustain_level:.1f} R:{instrument.release:.1f}"
                lines.append(f"  [dim]{adsr_info}[/dim]")
        else:
            lines.append("  [dim]Empty track[/dim]")
        
        return lines
    
    def _create_notation_lane(self, track: Track, total_loop_steps: int) -> str:
        """Create visual notation lane for the track."""
        if not track.patterns:
            return "[dim]Empty track[/dim]"
        
        # Get the first pattern (most common case)
        pattern = track.patterns[0]
        
        # Create visual representation
        notation_lines = []
        
        # Bar numbers line
        bar_numbers = []
        step_markers = []
        note_line = []
        velocity_line = []
        
        steps_to_show = min(total_loop_steps, len(pattern.steps))
        
        for step in range(steps_to_show):
            # Bar numbers (every 16 steps)
            if step % self.steps_per_bar == 0:
                bar_num = (step // self.steps_per_bar) + 1
                bar_numbers.append(f"{bar_num:2d}")
            else:
                bar_numbers.append("  ")
            
            # Step markers (every 4 steps gets a stronger marker)
            if step % 4 == 0:
                step_markers.append("|")
            else:
                step_markers.append("·")
            
            # Note and velocity representation
            note_event = pattern.steps[step]
            if note_event and note_event.note:
                # Show note name
                note_display = note_event.note[:2].ljust(2)  # C4, F#, etc.
                note_line.append(f"[bold yellow]{note_display}[/bold yellow]")
                
                # Show velocity as bar height
                velocity_bar = self._velocity_to_bar(note_event.velocity)
                velocity_line.append(f"[green]{velocity_bar}[/green]")
                
                # Highlight current playback position
                if step == self.current_step % total_loop_steps:
                    note_line[-1] = f"[bold red on white]{note_display}[/bold red on white]"
                    velocity_line[-1] = f"[bold red on white]{velocity_bar}[/bold red on white]"
            else:
                note_line.append("--")
                velocity_line.append("  ")
                
                # Show playback cursor on empty steps too
                if step == self.current_step % total_loop_steps:
                    note_line[-1] = "[bold red on white]--[/bold red on white]"
                    velocity_line[-1] = "[bold red on white]  [/bold red on white]"
        
        # Combine all lines
        notation_lines.append("Bars: " + "".join(bar_numbers))
        notation_lines.append("Step: " + "".join(step_markers))
        notation_lines.append("Note: " + " ".join(note_line))
        notation_lines.append("Vel:  " + " ".join(velocity_line))
        
        return "\n".join(notation_lines)
    
    def _velocity_to_bar(self, velocity: float) -> str:
        """Convert velocity (0.0-1.0) to visual bar representation."""
        if velocity <= 0:
            return " "
        elif velocity <= 0.25:
            return "▁"
        elif velocity <= 0.5:
            return "▃"
        elif velocity <= 0.75:
            return "▅"
        else:
            return "█"
    
    def _velocity_to_symbol(self, velocity: float) -> str:
        """Convert velocity to a single character symbol."""
        if velocity <= 0:
            return "·"
        elif velocity <= 0.25:
            return "▁"
        elif velocity <= 0.5:
            return "▃"
        elif velocity <= 0.75:
            return "▅"
        else:
            return "█"
    
    def _create_instrument_info(self, instrument: Instrument) -> str:
        """Create instrument information panel."""
        if not instrument:
            return "[dim]No instrument[/dim]"
        
        info_lines = []
        
        # Oscillators
        info_lines.append("[bold cyan]Oscillators:[/bold cyan]")
        for i, osc in enumerate(instrument.oscillators):
            waveform = osc.get('waveform', 'sine')
            amplitude = osc.get('amplitude', 1.0)
            info_lines.append(f"  {i+1}. {waveform.title()} ({amplitude:.2f})")
        
        # ADSR Envelope
        info_lines.append("\n[bold cyan]ADSR:[/bold cyan]")
        info_lines.append(f"  A: {instrument.attack:.2f}s")
        info_lines.append(f"  D: {instrument.decay:.2f}s")
        info_lines.append(f"  S: {instrument.sustain_level:.2f}")
        info_lines.append(f"  R: {instrument.release:.2f}s")
        
        # Filter (if present)
        if hasattr(instrument, 'filter_type') and instrument.filter_type:
            info_lines.append("\n[bold cyan]Filter:[/bold cyan]")
            info_lines.append(f"  Type: {instrument.filter_type}")
            if hasattr(instrument, 'filter_cutoff_hz'):
                info_lines.append(f"  Cutoff: {instrument.filter_cutoff_hz}Hz")
            if hasattr(instrument, 'filter_resonance_q'):
                info_lines.append(f"  Q: {instrument.filter_resonance_q:.2f}")
        
        return "\n".join(info_lines)


class PlaybackVisualizationWidget(Static):
    """Widget for showing overall playback progress and loop visualization."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def update_playback(self, current_step: int, total_steps: int, bpm: int, is_playing: bool = False):
        """Update playback visualization."""
        
        # Calculate progress
        progress = (current_step % total_steps) / total_steps if total_steps > 0 else 0
        
        # Create compact progress bar
        bar_width = 40
        filled_width = int(progress * bar_width)
        progress_bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        # Status indicator
        status = "▶" if is_playing else "⏸"
        status_color = "bold green" if is_playing else "bold yellow"
        
        # Create compact display
        current_beat = (current_step // 4) + 1
        total_beats = (total_steps // 4)
        
        display_text = f"[{status_color}]{status}[/{status_color}] BPM:{bpm} | Beat:{current_beat}/{total_beats} | [{progress_bar}] {progress*100:.0f}%"
        
        self.update(display_text)
