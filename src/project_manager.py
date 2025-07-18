import json
from typing import Optional

from src.music_structures import Composition


def save_project(composition: Composition, filepath: str) -> Optional[str]:
    """Saves the given composition to a JSON file.

    Args:
        composition: The Composition object to save.
        filepath: The path to the file where the project will be saved.

    Returns:
        None if successful, or an error message string if it fails.
    """
    try:
        with open(filepath, 'w') as f:
            json.dump(composition.to_dict(), f, indent=4)
        return None
    except IOError as e:
        return f"Error saving project to {filepath}: {e}"
    except Exception as e:
        return f"An unexpected error occurred during save: {e}"


def load_project(filepath: str) -> tuple[Optional[Composition], Optional[str]]:
    """Loads a composition from a JSON file.

    Args:
        filepath: The path to the project file.

    Returns:
        A tuple containing (Composition, None) if successful,
        or (None, error_message) if it fails.
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        composition = Composition.from_dict(data)
        return composition, None
    except FileNotFoundError:
        return None, f"Project file not found: {filepath}"
    except (json.JSONDecodeError, TypeError) as e:
        return None, f"Error reading project file {filepath}: {e}"
    except Exception as e:
        return None, f"An unexpected error occurred during load: {e}"
