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
        """Process audio through simple, musical reverb."""
        if not self.enabled:
            return audio_buffer
        
        # Get mix levels
        defaults = self.get_default_params()
        wet_level = self.params.get('wet_level', defaults['wet_level'])
        dry_level = self.params.get('dry_level', defaults['dry_level'])
        
        output = np.zeros_like(audio_buffer)
        
        for i, sample in enumerate(audio_buffer):
            # Input limiting
            sample = np.clip(sample, -0.95, 0.95)
            
            reverb_sum = 0.0
            
            # Process through parallel delay lines (classic Schroeder approach)
            for j, (buffer, length) in enumerate(zip(self.delay_buffers, self.delay_lengths)):
                # Read delayed sample
                delayed = buffer[self.delay_indices[j]]
                
                # Simple lowpass damping filter
                self.lowpass_state[j] = (delayed * (1 - self.damping_coeff) + 
                                       self.lowpass_state[j] * self.damping_coeff)
                
                # Feedback with gentle limiting
                feedback = self.lowpass_state[j] * self.feedback
                if feedback > 0.8:
                    feedback = 0.8
                elif feedback < -0.8:
                    feedback = -0.8
                
                # Write new sample to delay line
                buffer[self.delay_indices[j]] = sample + feedback
                
                # Advance delay pointer
                self.delay_indices[j] = (self.delay_indices[j] + 1) % length
                
                # Sum delayed outputs with slight gain variation for naturalness
                gain = 0.125 + j * 0.01  # Slight variation per delay line
                reverb_sum += delayed * gain
            
            # Simple output processing
            reverb_sample = reverb_sum * 0.7  # Overall reverb level
            
            # Mix dry and wet
            output[i] = dry_level * sample + wet_level * reverb_sample
            
            # Final gentle limiting
            if output[i] > 0.95:
                output[i] = 0.95
            elif output[i] < -0.95:
                output[i] = -0.95
        
        return output
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReverbEffect':
        """Create reverb instance from dictionary."""
        # Extract parameters, excluding 'type'
        params = {k: v for k, v in data.items() if k != 'type'}
        return cls(**params)


def create_effect_from_dict(effect_data: Dict[str, Any]) -> BaseEffect:
    """Factory function to create effects from dictionary data."""
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
