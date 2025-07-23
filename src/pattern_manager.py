import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from .music_structures import Pattern, NoteEvent

class PatternManager:
    """Manages a library of saved patterns for reuse and arrangement."""
    
    def __init__(self, patterns_dir: str = "patterns"):
        self.patterns_dir = patterns_dir
        self.is_test_mode = patterns_dir.startswith("test_") or "test" in patterns_dir.lower()
        self._ensure_patterns_directory()
        
    def _ensure_patterns_directory(self):
        """Create patterns directory if it doesn't exist."""
        if not os.path.exists(self.patterns_dir):
            os.makedirs(self.patterns_dir)
            
    def save_pattern(self, pattern: Pattern, name: str, tags: List[str] = None, 
                    instrument_id: str = None) -> bool:
        """Save a pattern to the library with metadata."""
        try:
            pattern_data = {
                'name': name,
                'created_at': datetime.now().isoformat(),
                'tags': tags or [],
                'instrument_id': instrument_id,
                'pattern': pattern.to_dict()
            }
            
            filename = f"{name.replace(' ', '_').lower()}.json"
            filepath = os.path.join(self.patterns_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(pattern_data, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving pattern: {e}")
            return False
            
    def load_pattern(self, name: str) -> Optional[Tuple[Pattern, Dict]]:
        """Load a pattern from the library."""
        try:
            filename = f"{name.replace(' ', '_').lower()}.json"
            filepath = os.path.join(self.patterns_dir, filename)
            
            if not os.path.exists(filepath):
                return None
                
            with open(filepath, 'r') as f:
                pattern_data = json.load(f)
                
            pattern = Pattern.from_dict(pattern_data['pattern'])
            metadata = {
                'name': pattern_data['name'],
                'created_at': pattern_data['created_at'],
                'tags': pattern_data['tags'],
                'instrument_id': pattern_data.get('instrument_id')
            }
            
            return pattern, metadata
        except Exception as e:
            print(f"Error loading pattern: {e}")
            return None
            
    def list_patterns(self) -> List[Dict]:
        """List all patterns in the library with their metadata."""
        patterns = []
        
        if not os.path.exists(self.patterns_dir):
            return patterns
            
        for filename in os.listdir(self.patterns_dir):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(self.patterns_dir, filename)
                    with open(filepath, 'r') as f:
                        pattern_data = json.load(f)
                        
                    patterns.append({
                        'filename': filename,
                        'name': pattern_data['name'],
                        'created_at': pattern_data['created_at'],
                        'tags': pattern_data['tags'],
                        'instrument_id': pattern_data.get('instrument_id'),
                        'steps': len(pattern_data['pattern']['steps'])
                    })
                except Exception as e:
                    print(f"Error reading pattern {filename}: {e}")
                    continue
                    
        return sorted(patterns, key=lambda x: x['created_at'], reverse=True)
        
    def delete_pattern(self, name: str) -> bool:
        """Delete a pattern from the library."""
        try:
            filename = f"{name.replace(' ', '_').lower()}.json"
            filepath = os.path.join(self.patterns_dir, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            print(f"Error deleting pattern: {e}")
            return False
            
    def search_patterns(self, query: str = "", tags: List[str] = None) -> List[Dict]:
        """Search patterns by name or tags."""
        all_patterns = self.list_patterns()
        
        if not query and not tags:
            return all_patterns
            
        filtered = []
        for pattern in all_patterns:
            match = False
            
            # Search by name
            if query and query.lower() in pattern['name'].lower():
                match = True
                
            # Search by tags
            if tags:
                pattern_tags = [tag.lower() for tag in pattern['tags']]
                if any(tag.lower() in pattern_tags for tag in tags):
                    match = True
                    
            if match:
                filtered.append(pattern)
                
        return filtered
        
    def create_variation(self, pattern: Pattern, variation_type: str = "fill") -> Pattern:
        """Create a variation of an existing pattern."""
        import random
        
        new_pattern = Pattern(steps=pattern.steps.copy())
        
        if variation_type == "fill":
            # Add random notes to empty steps
            for i, step in enumerate(new_pattern.steps):
                if not step or not step.note:
                    if random.random() < 0.3:  # 30% chance to add a note
                        # Use a random note from existing notes in the pattern
                        existing_notes = [s.note for s in pattern.steps if s and s.note]
                        if existing_notes:
                            random_note = random.choice(existing_notes)
                            new_pattern.steps[i] = NoteEvent(
                                note=random_note,
                                velocity=random.randint(50, 100),
                                duration=1
                            )
                            
        elif variation_type == "sparse":
            # Remove some notes randomly
            for i, step in enumerate(new_pattern.steps):
                if step and step.note and random.random() < 0.3:  # 30% chance to remove
                    new_pattern.steps[i] = None
                    
        elif variation_type == "velocity":
            # Vary velocity of existing notes
            for step in new_pattern.steps:
                if step and step.note:
                    variation = random.randint(-20, 20)
                    step.velocity = max(1, min(127, step.velocity + variation))
                    
        elif variation_type == "swing":
            # Add slight timing variations (would need more complex implementation)
            # For now, just vary durations slightly
            for step in new_pattern.steps:
                if step and step.note:
                    if random.random() < 0.2:  # 20% chance
                        step.duration = max(1, step.duration + random.choice([-1, 1]))
                        
        return new_pattern
        
    def save_composition(self, composition, instruments: dict, name: str, tags: List[str] = None) -> bool:
        """Save a full composition (all tracks and instruments) to the library."""
        try:
            composition_data = {
                'name': name,
                'created_at': datetime.now().isoformat(),
                'tags': tags or [],
                'type': 'composition',  # Mark as composition vs single pattern
                'composition': composition.to_dict(),
                'instruments': {inst_id: inst.to_dict() for inst_id, inst in instruments.items()}
            }
            
            filename = f"{name.replace(' ', '_').lower()}_comp.json"
            filepath = os.path.join(self.patterns_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(composition_data, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving composition: {e}")
            return False
            
    def load_composition(self, name: str):
        """Load a full composition from the library."""
        try:
            filename = f"{name.replace(' ', '_').lower()}_comp.json"
            filepath = os.path.join(self.patterns_dir, filename)
            
            if not os.path.exists(filepath):
                return None
                
            with open(filepath, 'r') as f:
                composition_data = json.load(f)
                
            # Reconstruct composition and instruments
            from .music_structures import Composition
            from .synthesis import Instrument
            
            composition = Composition.from_dict(composition_data['composition'])
            instruments = {
                inst_id: Instrument.from_dict(inst_data) 
                for inst_id, inst_data in composition_data['instruments'].items()
            }
            
            metadata = {
                'name': composition_data['name'],
                'created_at': composition_data['created_at'],
                'tags': composition_data['tags'],
                'type': composition_data.get('type', 'composition')
            }
            
            return composition, instruments, metadata
        except Exception as e:
            print(f"Error loading composition: {e}")
            return None
            
    def list_all_items(self) -> List[Dict]:
        """List all patterns and compositions in the library."""
        items = []
        
        if not os.path.exists(self.patterns_dir):
            return items
            
        for filename in os.listdir(self.patterns_dir):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(self.patterns_dir, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    # Determine if it's a pattern or composition
                    item_type = data.get('type', 'pattern')
                    
                    if item_type == 'composition':
                        # For compositions, count tracks instead of steps
                        track_count = len(data['composition']['tracks'])
                        items.append({
                            'filename': filename,
                            'name': data['name'],
                            'created_at': data['created_at'],
                            'tags': data['tags'],
                            'type': 'composition',
                            'tracks': track_count,
                            'bpm': data['composition'].get('bpm', 'N/A')
                        })
                    else:
                        # Regular pattern
                        items.append({
                            'filename': filename,
                            'name': data['name'],
                            'created_at': data['created_at'],
                            'tags': data['tags'],
                            'type': 'pattern',
                            'instrument_id': data.get('instrument_id'),
                            'steps': len(data['pattern']['steps'])
                        })
                        
                except Exception as e:
                    print(f"Error reading file {filename}: {e}")
                    continue
                    
        return sorted(items, key=lambda x: x['created_at'], reverse=True)
            
    def safe_cleanup_test_directory(self) -> bool:
        """Safely remove test pattern directory. Only works in test mode."""
        if not self.is_test_mode:
            print(f"ERROR: Attempted to cleanup non-test directory '{self.patterns_dir}'. This is not allowed for safety.")
            return False
            
        try:
            import shutil
            if os.path.exists(self.patterns_dir):
                shutil.rmtree(self.patterns_dir)
                return True
            return True  # Directory doesn't exist, that's fine
        except Exception as e:
            print(f"Error cleaning up test directory: {e}")
            return False
