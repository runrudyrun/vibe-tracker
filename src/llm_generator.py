import os
import google.generativeai as genai
import json
from openai import OpenAI

# --- System Prompt ---
SYSTEM_PROMPT = """You are an expert AI music composer. 
You will be given the current state of a musical composition in a JSON object, followed by a user request.
Your task is to modify the composition based on the user's request.
- If the user wants to add something (e.g., 'add a bassline'), add a new track or notes without removing existing ones.
- If the user wants to change something (e.g., 'make the tempo faster'), modify the existing values.
- If the user wants to remove something, remove the specified track or notes.
- If the user asks for a completely new song, you can replace the entire composition.

**Musical Rules:**
1.  **Pattern Length:** All patterns must be exactly 64 steps long (from step 0 to 63).
2.  **Seamless Looping:** Patterns must loop perfectly. The rhythm must flow continuously from the last step (63) back to the first (0) without a noticeable pause. To achieve this, **avoid ending patterns with long silence**. Place notes near the very end of the pattern (e.g., on steps 60, 61, 62, or 63) to create a smooth, uninterrupted transition back to the start.
3.  **Density:** Fill the patterns with musical content. Avoid long stretches of silence unless it's a deliberate artistic choice for a specific sound like a crash cymbal.
4.  **Note Duration:** You can specify the length of a note using the `duration` field, measured in steps. For long, sustained notes (drones), use a high `duration` value (e.g., 64). For short, percussive notes, use a `duration` of 1.
- **Additive Synthesis Guide (Oscillators)**: Create complex, rich sounds by layering multiple simple waveforms. Instead of a single `waveform`, you now define a list of `oscillators`.
    - `oscillators`: A list of one or more oscillator objects.
    - Each oscillator object has a `waveform` (e.g., 'sawtooth', 'sine') and an `amplitude` (from 0.0 to 1.0).
    - The sum of amplitudes should ideally be around 1.0 to avoid clipping.
    - *Example*: To create a rich pad, combine a 'sawtooth' wave at 60% amplitude with a 'sine' wave at 40% amplitude: `"oscillators": [{"waveform": "sawtooth", "amplitude": 0.6}, {"waveform": "sine", "amplitude": 0.4}]`
- **Drum Synthesis Guide**: For a powerful **Kick Drum**, use a single `sine` oscillator with a very short attack and decay. For **Snare Drums** and **Hi-Hats**, use the `noise` waveform.
- **Subtractive Synthesis Guide (Filters)**: You can shape the timbre of any instrument using a filter. This is great for making sounds softer, brighter, or more expressive.
    - `filter_type`: Set to `"lowpass"` to cut high frequencies, `"highpass"` to cut low frequencies, or `"bandpass"` for mid-range focus.
    - `filter_cutoff_hz`: The frequency (in Hz) where the filter starts cutting. A low value (e.g., 500-1000 Hz) makes the sound dark and muffled (good for pads and basses). A high value (e.g., 5000-15000 Hz) makes it bright and sharp (good for leads).
    - `filter_resonance_q`: A peak at the cutoff frequency. A value around 0.7 is neutral. Higher values (e.g., 2-5) create a more resonant, "buzzy" sound.
- **Audio Effects Guide**: Add professional audio effects to any instrument to enhance the sound and create spatial depth.
    - `effects`: An optional list of effect objects applied to the instrument's output.
    - **Reverb Effect**: Creates spatial depth and ambience. Perfect for vocals, pads, leads, and drums.
        - `type`: Must be `"reverb"`
        - `room_size`: 0.0 to 1.0 - Size of the virtual room (0.2 = small room, 0.5 = medium hall, 0.8 = large cathedral)
        - `damping`: 0.0 to 1.0 - High frequency damping (0.2 = bright reverb, 0.8 = dark, muffled reverb)
        - `wet_level`: 0.0 to 1.0 - Amount of reverb signal (0.1 = subtle, 0.5 = prominent, 0.8 = very wet)
        - `dry_level`: 0.0 to 1.0 - Amount of original signal (usually 0.7-1.0 to maintain clarity)
        - `enabled`: true/false - Whether the effect is active
    - **Effect Usage Examples**:
        - Subtle vocal reverb: `{"type": "reverb", "room_size": 0.3, "wet_level": 0.2, "dry_level": 0.8}`
        - Dramatic pad reverb: `{"type": "reverb", "room_size": 0.7, "wet_level": 0.5, "dry_level": 0.6}`
        - Snare drum reverb: `{"type": "reverb", "room_size": 0.4, "damping": 0.6, "wet_level": 0.3}`

    - **Delay Effect ("delay")**:
        - `type`: Must be `"delay"`
        - `delay_time`: 0.01 to 2.0 - Delay time in seconds (0.125 = 1/8 note at 120 BPM, 0.25 = 1/4 note, 0.5 = 1/2 note)
        - `feedback`: 0.0 to 0.9 - Amount of delayed signal fed back for repeating echoes (0.3 = subtle, 0.6 = prominent)
        - `damping`: 0.0 to 1.0 - High frequency damping for natural decay (0.2 = bright, 0.5 = warm)
        - `wet_level`: 0.0 to 1.0 - Amount of delay signal (0.2 = subtle, 0.4 = prominent)
        - `dry_level`: 0.0 to 1.0 - Amount of original signal (usually 0.8-1.0)
        - `enabled`: true/false - Whether the effect is active
    - **Delay Usage Examples**:
        - Vocal echo: `{"type": "delay", "delay_time": 0.25, "feedback": 0.3, "wet_level": 0.2}`
        - Guitar delay: `{"type": "delay", "delay_time": 0.375, "feedback": 0.5, "damping": 0.3, "wet_level": 0.4}`
        - Dub delay: `{"type": "delay", "delay_time": 0.5, "feedback": 0.7, "wet_level": 0.6}`

You must respond with a single, valid JSON object representing the *complete, updated* composition. Do not respond with anything else.
The JSON structure must be:

{
  "bpm": <integer>,
  "instruments": [
    {
      "name": "<string>",
      "oscillators": [
        {"waveform": "<string, one of 'sine', 'square', 'sawtooth', 'triangle', 'noise'>", "amplitude": <float, 0.0 to 1.0>}
      ],
      "attack": <float>,
      "decay": <float>,
      "sustain_level": <float>,
      "release": <float>,
      // Optional Filter Parameters
      "filter_type": "lowpass", // Supported types: 'lowpass', 'highpass', 'bandpass'
      "filter_cutoff_hz": 4000, // Frequency in Hz (e.g., 500 for dark, 15000 for bright)
      "filter_resonance_q": 0.707, // A value from 0.707 (no resonance) to 10 (high resonance)
      // Optional Effects Chain
      "effects": [
        {
          "type": "reverb",
          "room_size": 0.5, // 0.0 to 1.0
          "damping": 0.5,   // 0.0 to 1.0
          "wet_level": 0.3, // 0.0 to 1.0
          "dry_level": 0.7, // 0.0 to 1.0
          "enabled": true   // true/false
        }
        // Add more effects here if needed
      ]
    }
  ],
  "tracks": [
    {
      "instrument_name": "<string>",
      "notes": [
        {"step": <integer>, "note": "<string>", "duration": <integer>}
      ]
    }
  ]
}
"""

class LLMGenerator:
    def __init__(self, provider="auto"):
        self.provider = provider
        self.client = None
        self.model = None
        self.model_name = None
        
        # Check for explicit provider override first
        llm_provider_override = os.getenv("LLM_PROVIDER")
        if llm_provider_override:
            self.provider = llm_provider_override.lower()
        elif provider == "auto":
            # Auto-select provider based on available credentials
            if os.getenv("HF_TOKEN"):
                self.provider = "huggingface"
            elif os.getenv("GOOGLE_API_KEY"):
                self.provider = "gemini"
            else:
                raise ValueError("No LLM provider credentials found. Set HF_TOKEN or GOOGLE_API_KEY")
        
        # Initialize the selected provider
        if self.provider == "huggingface":
            self._init_huggingface()
        elif self.provider == "gemini":
            self._init_gemini()
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _init_huggingface(self):
        """Initialize Hugging Face provider"""
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise ValueError("HF_TOKEN not found in environment")
        
        self.client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=hf_token
        )
        self.model_name = os.getenv("HF_MODEL", "openai/gpt-oss-20b")
        print(f"[LLM Generator] Using Hugging Face: {self.model_name}")
    
    def _init_gemini(self):
        """Initialize Gemini provider"""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model_name = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=SYSTEM_PROMPT
        )
        print(f"[LLM Generator] Using Gemini: {self.model_name}")

    def generate_music_from_prompt(self, user_prompt: str, context_composition: dict = None):
        """Generate music data from a user prompt with optional context
        Returns: (music_data, error, raw_response)
        """
        if self.provider == "huggingface":
            return self._generate_huggingface(user_prompt, context_composition)
        elif self.provider == "gemini":
            return self._generate_gemini(user_prompt, context_composition)
        else:
            return None, f"Unknown provider: {self.provider}", None
    
    def _generate_huggingface(self, user_prompt: str, context_composition: dict = None):
        """Generate using Hugging Face API
        Returns: (music_data, error, raw_response)
        """
        raw_response = None
        try:
            messages = [
                {"role": "system", "content": self._get_hf_system_prompt()}
            ]
            
            if context_composition:
                context_json = json.dumps(context_composition, indent=2)
                messages.append({
                    "role": "user",
                    "content": f"Here is the current composition:\n\n```json\n{context_json}\n```"
                })
            
            messages.append({"role": "user", "content": f"User request: '{user_prompt}'"})
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=4096,  # Increased for complex compositions
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            if not response.choices:
                error_msg = "HF API returned no choices"
                print(f"[LLM Generator] {error_msg}")
                return None, error_msg, None
            
            raw_response = response.choices[0].message.content
            
            if raw_response is None:
                error_msg = "HF API returned None content"
                print(f"[LLM Generator] {error_msg}")
                return None, error_msg, None
            
            try:
                music_data = json.loads(raw_response)
                
                # Fix HF API issue: remove extra "type" field if present
                if "type" in music_data and music_data["type"] == "object":
                    music_data.pop("type")
                
                return music_data, None, raw_response
            except json.JSONDecodeError as json_err:
                # Try to fix truncated JSON by detecting incomplete structure
                if "Expecting value" in str(json_err) or "Expecting" in str(json_err):
                    # Find the last complete object/array and truncate there
                    fixed_json = self._fix_truncated_json(raw_response)
                    if fixed_json:
                        try:
                            music_data = json.loads(fixed_json)
                            if "type" in music_data and music_data["type"] == "object":
                                music_data.pop("type")
                            return music_data, None, raw_response
                        except json.JSONDecodeError:
                            pass
                
                error_msg = f"JSON parsing failed: {json_err}"
                print(f"[LLM Generator] {error_msg}")
                return None, error_msg, raw_response
            
        except Exception as e:
            error_msg = str(e)
            print(f"[LLM Generator] Hugging Face Error: {error_msg}")
            return None, error_msg, raw_response
    
    def _fix_truncated_json(self, raw_response: str) -> str:
        """Try to fix truncated JSON by finding the last complete structure"""
        try:
            # Find the last complete closing brace for the main object
            lines = raw_response.split('\n')
            
            # Work backwards to find a valid truncation point
            for i in range(len(lines) - 1, -1, -1):
                truncated = '\n'.join(lines[:i])
                
                # Count braces and brackets to see if we can close them
                open_braces = truncated.count('{')
                close_braces = truncated.count('}')
                open_brackets = truncated.count('[')
                close_brackets = truncated.count(']')
                
                # If we have more opens than closes, try to close them
                if open_braces > close_braces or open_brackets > close_brackets:
                    fixed = truncated
                    
                    # Close any open arrays first
                    while open_brackets > close_brackets:
                        fixed += '\n]'
                        close_brackets += 1
                    
                    # Close any open objects
                    while open_braces > close_braces:
                        fixed += '\n}'
                        close_braces += 1
                    
                    # Test if this creates valid JSON
                    try:
                        json.loads(fixed)
                        return fixed
                    except json.JSONDecodeError:
                        continue
            
            return None
        except Exception:
            return None
    
    def _generate_gemini(self, user_prompt: str, context_composition: dict = None):
        """Generate using Gemini API
        Returns: (music_data, error, raw_response)
        """
        raw_response = None
        try:
            full_prompt = []
            if context_composition:
                context_json = json.dumps(context_composition, indent=2)
                full_prompt.append(f"Here is the current composition:\n\n```json\n{context_json}\n```")
            
            full_prompt.append(f"User request: '{user_prompt}'")
            final_prompt_str = "\n\n".join(full_prompt)

            response = self.model.generate_content(final_prompt_str)
            raw_response = response.text
            
            try:
                json_text = raw_response.strip().replace('```json', '').replace('```', '').strip()
                music_data = json.loads(json_text)
                return music_data, None, raw_response
            except json.JSONDecodeError as json_err:
                error_msg = f"JSON parsing failed: {json_err}"
                print(f"[LLM Generator] {error_msg}")
                return None, error_msg, raw_response
            
        except Exception as e:
            error_msg = str(e)
            print(f"[LLM Generator] Gemini Error: {error_msg}")
            return None, error_msg, raw_response
    
    def _get_hf_system_prompt(self):
        """Get system prompt optimized for Hugging Face API"""
        return """You are an expert AI music composer. Generate music compositions in JSON format.

IMPORTANT: Respond with ONLY a valid JSON object. No explanatory text or markdown.

Musical Rules:
1. Pattern Length: All patterns must be exactly 64 steps long (0-63)
2. Seamless Looping: Place notes near end (steps 60-63) for smooth transitions  
3. Density: Fill patterns with musical content
4. Note Duration: Use duration field (1 for percussive, 64 for sustained)

Synthesis Guide:
- oscillators: List of waveform objects with amplitude (sum ≈ 1.0)
- Waveforms: 'sine', 'square', 'sawtooth', 'triangle', 'noise'
- Filters: 'lowpass', 'highpass', 'bandpass' with cutoff_hz and resonance_q
- Effects: reverb and delay with appropriate parameters

JSON Structure:
{
  "bpm": <integer>,
  "instruments": [
    {
      "name": "<string>",
      "oscillators": [{"waveform": "<string>", "amplitude": <float>}],
      "attack": <float>, "decay": <float>, "sustain_level": <float>, "release": <float>,
      "filter_type": "<string>", "filter_cutoff_hz": <integer>, "filter_resonance_q": <float>,
      "effects": [{"type": "reverb", "room_size": <float>, "damping": <float>, "wet_level": <float>, "dry_level": <float>, "enabled": <bool>}]
    }
  ],
  "tracks": [
    {"instrument_name": "<string>", "notes": [{"step": <integer>, "note": "<string>", "duration": <integer>}]}
  ]
}"""
    
    def get_provider_info(self):
        """Get information about the current provider"""
        if self.provider == "huggingface":
            return f"Hugging Face ({self.model_name})"
        elif self.provider == "gemini":
            return "Google Gemini (gemini-2.5-flash)"
        else:
            return f"Unknown ({self.provider})"

if __name__ == '__main__':
    # Example usage:
    try:
        generator = LLMGenerator()
        user_input = "a fast, aggressive techno beat with a driving kick and a noisy snare"
        
        print(f"Sending prompt to {generator.get_provider_info()}: '{user_input}'")
        data, error = generator.generate_music_from_prompt(user_input)

        if error:
            print(f"An error occurred: {error}")
        else:
            print(f"\n--- Successfully received data from {generator.get_provider_info()} ---")
            print(json.dumps(data, indent=2))
            print("\n---------------------------------------------")
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("\nTo use Hugging Face: Get token from https://huggingface.co/settings/tokens")
        print("Then set: export HF_TOKEN=your_token_here")
        print("\nTo use Gemini: Set GOOGLE_API_KEY in your .env file")
