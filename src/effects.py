#!/usr/bin/env python3
"""
Audio Effects Module for Vibe-Tracker

This module provides audio effects that can be applied to instruments.
Effects are designed to work with the LLM-driven workflow - they must be
serializable to/from JSON and compatible with the LLM prompt system.

Architecture:
- BaseEffect: Abstract base class for all effects
- ReverbEffect: Algorithmic reverb implementation
- Integration with Instrument class for per-instrument effects processing
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

# Import sample rate from synthesis module
try:
    from .synthesis import SAMPLE_RATE
except ImportError:
    # Fallback for direct execution
    from synthesis import SAMPLE_RATE

logger = logging.getLogger(__name__)


class BaseEffect(ABC):
    """Abstract base class for all audio effects."""
    
    def __init__(self, effect_type: str, **params):
        """
        Initialize the effect with given parameters.
        
        Args:
            effect_type: Type identifier for the effect (e.g., "reverb", "delay")
            **params: Effect-specific parameters
        """
        self.effect_type = effect_type
        self.enabled = params.get('enabled', True)
        
        # Merge provided params with defaults
        defaults = self.get_default_params()
        self.params = defaults.copy()
        self.params.update(params)
        
        self._initialize_effect()
    
    @abstractmethod
    def _initialize_effect(self):
        """Initialize effect-specific state and buffers."""
        pass
    
    @abstractmethod
    def process(self, audio_buffer: np.ndarray) -> np.ndarray:
        """
        Process audio through the effect.
        
        Args:
            audio_buffer: Input audio samples (1D numpy array)
            
        Returns:
            Processed audio samples (same shape as input)
        """
        pass
    
    @abstractmethod
    def get_default_params(self) -> Dict[str, Any]:
        """Return dictionary of default parameters for this effect."""
        pass
    
    def set_param(self, param_name: str, value: Any):
        """Set a parameter value and reinitialize if necessary."""
        if param_name in self.get_default_params() or param_name == 'enabled':
            self.params[param_name] = value
            if param_name == 'enabled':
                self.enabled = value
            else:
                self._initialize_effect()
        else:
            raise ValueError(f"Unknown parameter '{param_name}' for {self.effect_type}")
    
    def get_param(self, param_name: str, default=None):
        """Get a parameter value."""
        return self.params.get(param_name, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize effect to dictionary for LLM compatibility."""
        result = {
            'type': self.effect_type,
            'enabled': self.enabled
        }
        # Add all non-default parameters
        defaults = self.get_default_params()
        for key, value in self.params.items():
            if key != 'enabled' and (key not in defaults or defaults[key] != value):
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseEffect':
        """Create effect instance from dictionary."""
        effect_type = data.get('type')
        if effect_type == 'reverb':
            return ReverbEffect.from_dict(data)
        else:
            raise ValueError(f"Unknown effect type: {effect_type}")


class ReverbEffect(BaseEffect):
    """
    Algorithmic reverb effect using multiple delay lines and feedback.
    
    This implements a simplified reverb algorithm with:
    - Multiple delay lines for early reflections
    - Feedback for sustain
    - Damping for high frequency roll-off
    - Wet/dry mix control
    """
    
    def __init__(self, **params):
        """Initialize reverb with parameters."""
        super().__init__("reverb", **params)
    
    def get_default_params(self) -> Dict[str, Any]:
        """Default reverb parameters optimized for LLM usage."""
        return {
            'room_size': 0.5,      # 0.0 to 1.0 - size of the virtual room
            'damping': 0.5,        # 0.0 to 1.0 - high frequency damping  
            'wet_level': 0.3,      # 0.0 to 1.0 - reverb signal level
            'dry_level': 0.7,      # 0.0 to 1.0 - original signal level
        }
    
    def _initialize_effect(self):
        """Initialize simple, musical reverb based on classic Schroeder design."""
        # Get parameters with defaults
        defaults = self.get_default_params()
        room_size = self.params.get('room_size', defaults['room_size'])
        damping = self.params.get('damping', defaults['damping'])
        
        # Simple, proven delay times (in samples at 44.1kHz)
        # Based on classic reverb research - these sound musical
        base_delays = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617]
        
        # Scale by room size
        room_scale = 0.5 + room_size * 0.5  # Conservative scaling
        self.delay_lengths = [int(delay * room_scale) for delay in base_delays]
        
        # Initialize delay buffers
        self.delay_buffers = [np.zeros(length) for length in self.delay_lengths]
        self.delay_indices = [0] * len(self.delay_lengths)
        
        # Simple feedback - proven to work well
        self.feedback = 0.7 + room_size * 0.2  # Higher feedback for lush sound
        
        # Simple damping filter state
        self.damping_coeff = damping * 0.5  # Gentler damping
        self.lowpass_state = [0.0] * len(self.delay_lengths)
    
    def process(self, audio_buffer: np.ndarray) -> np.ndarray:
        """Process audio through fully vectorized, high-performance reverb."""
        if not self.enabled:
            return audio_buffer
        
        # Get mix levels
        defaults = self.get_default_params()
        wet_level = self.params.get('wet_level', defaults['wet_level'])
        dry_level = self.params.get('dry_level', defaults['dry_level'])
        
        # Input limiting
        input_buffer = np.clip(audio_buffer, -0.95, 0.95)
        buffer_size = len(input_buffer)
        
        # Initialize reverb output
        reverb_sum = np.zeros_like(input_buffer)
        
        # Process each delay line (still need minimal loop for separate delay lines)
        for j, (delay_buffer, length) in enumerate(zip(self.delay_buffers, self.delay_lengths)):
            # Current read position
            read_pos = self.delay_indices[j]
            
            # Create arrays for vectorized operations
            read_indices = (read_pos + np.arange(buffer_size)) % length
            write_indices = read_indices  # Same positions for write
            
            # Read delayed samples (vectorized)
            delayed_samples = delay_buffer[read_indices]
            
            # Apply simple damping filter (vectorized)
            # For simplicity, use a basic one-pole lowpass
            damped_samples = delayed_samples * (1 - self.damping_coeff)
            
            # Feedback calculation (vectorized)
            feedback_samples = damped_samples * self.feedback
            feedback_samples = np.clip(feedback_samples, -0.8, 0.8)
            
            # Write new samples to delay buffer (input + feedback)
            new_samples = input_buffer + feedback_samples
            delay_buffer[write_indices] = new_samples
            
            # Update delay index for next call
            self.delay_indices[j] = (read_pos + buffer_size) % length
            
            # Add this delay line's contribution
            gain = 0.125 + j * 0.01  # Slight variation per delay line
            reverb_sum += delayed_samples * gain
        
        # Overall reverb processing (vectorized)
        reverb_signal = reverb_sum * 0.7
        
        # Mix dry and wet signals (vectorized)
        output = dry_level * input_buffer + wet_level * reverb_signal
        
        # Final limiting (vectorized)
        output = np.clip(output, -0.95, 0.95)
        
        return output
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReverbEffect':
        """Create reverb instance from dictionary."""
        # Extract parameters, excluding 'type'
        params = {k: v for k, v in data.items() if k != 'type'}
        return cls(**params)


class DelayEffect(BaseEffect):
    """High-performance vectorized delay/echo effect."""
    
    def __init__(self, **params):
        """Initialize delay with parameters."""
        super().__init__("delay", **params)
        
        # Get delay time parameter
        delay_time = self.params.get('delay_time', 0.25)
        
        # Calculate delay buffer size (44.1kHz sample rate assumed)
        sample_rate = 44100
        max_delay_samples = int(sample_rate * 2.0)  # 2 seconds max delay
        self.delay_samples = int(sample_rate * delay_time)
        self.delay_samples = min(self.delay_samples, max_delay_samples)
        
        # Create delay buffer
        self.delay_buffer = np.zeros(max_delay_samples)
        self.write_index = 0
    
    @staticmethod
    def get_default_params() -> Dict[str, Any]:
        """Get default delay parameters."""
        return {
            'delay_time': 0.25,    # 250ms delay
            'feedback': 0.4,       # Feedback amount (0.0-0.9)
            'damping': 0.2,        # High-frequency damping (0.0-1.0)
            'wet_level': 0.3,      # Delay signal level
            'dry_level': 1.0,      # Original signal level
            'enabled': True
        }
    
    def process(self, audio_buffer: np.ndarray) -> np.ndarray:
        """Process audio through vectorized delay effect."""
        if not self.enabled:
            return audio_buffer
        
        # Get parameters
        feedback = self.params.get('feedback', 0.4)
        damping = self.params.get('damping', 0.2)
        wet_level = self.params.get('wet_level', 0.3)
        dry_level = self.params.get('dry_level', 1.0)
        
        # Limit feedback to prevent runaway
        feedback = np.clip(feedback, 0.0, 0.9)
        
        # Input limiting
        input_buffer = np.clip(audio_buffer, -0.95, 0.95)
        buffer_size = len(input_buffer)
        
        # Calculate read indices for vectorized operation
        read_positions = (self.write_index - self.delay_samples + np.arange(buffer_size)) % len(self.delay_buffer)
        
        # Read delayed samples (vectorized)
        delayed_samples = self.delay_buffer[read_positions]
        
        # Apply damping to feedback signal (simple high-cut)
        feedback_samples = delayed_samples * feedback
        if damping > 0.01:
            feedback_samples = feedback_samples * (1.0 - damping * 0.3)
        
        # Calculate new samples to write to delay buffer
        new_samples = input_buffer + feedback_samples
        
        # Write to delay buffer (vectorized)
        write_indices = (self.write_index + np.arange(buffer_size)) % len(self.delay_buffer)
        self.delay_buffer[write_indices] = new_samples
        
        # Update write index for next call
        self.write_index = (self.write_index + buffer_size) % len(self.delay_buffer)
        
        # Mix dry and wet signals (vectorized)
        output = dry_level * input_buffer + wet_level * delayed_samples
        
        # Final limiting (vectorized)
        output = np.clip(output, -0.95, 0.95)
        
        return output
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DelayEffect':
        """Create delay instance from dictionary."""
        # Extract parameters, excluding 'type'
        params = {k: v for k, v in data.items() if k != 'type'}
        return cls(**params)


def create_effect_from_dict(effect_data: Dict[str, Any]) -> BaseEffect:
    """Factory function to create effects from dictionary data."""
    effect_type = effect_data.get('type', '').lower()
    
    if effect_type == 'reverb':
        return ReverbEffect.from_dict(effect_data)
    elif effect_type == 'delay':
        return DelayEffect.from_dict(effect_data)
    else:
        # Fallback to base class
        return BaseEffect.from_dict(effect_data)


def create_effects_from_list(effects_data: List[Dict[str, Any]]) -> List[BaseEffect]:
    """Create a list of effects from list of dictionaries."""
    effects = []
    for effect_data in effects_data:
        try:
            effect = create_effect_from_dict(effect_data)
            effects.append(effect)
        except Exception as e:
            logger.warning(f"Failed to create effect from data {effect_data}: {e}")
    return effects
