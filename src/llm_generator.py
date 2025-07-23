import os
import google.generativeai as genai
import json
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv() # Load variables from .env file
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

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
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=SYSTEM_PROMPT
        )

    def generate_music_from_prompt(self, user_prompt: str, context_composition: dict = None):
        """Sends the user prompt and context to the LLM to get a modified composition."""
        
        full_prompt = []
        if context_composition:
            context_json = json.dumps(context_composition, indent=2)
            full_prompt.append(f"Here is the current composition:\n\n```json\n{context_json}\n```")
        
        full_prompt.append(f"User request: '{user_prompt}'")
        
        final_prompt_str = "\n\n".join(full_prompt)

        try:
            response = self.model.generate_content(final_prompt_str)
            # Clean up the response to get only the JSON part
            json_text = response.text.strip().replace('```json', '').replace('```', '').strip()
            
            # Parse the JSON string into a Python dictionary
            music_data = json.loads(json_text)
            return music_data, None
        except Exception as e:
            print(f"[LLM Generator] Error: {e}")
            return None, str(e)

if __name__ == '__main__':
    # Example usage:
    generator = LLMGenerator()
    # user_input = "Create a slow, melancholic synthwave track with a simple bassline and a lead melody."
    user_input = "a fast, aggressive techno beat with a driving kick and a noisy snare"
    
    print(f"Sending prompt to Gemini: '{user_input}'")
    data, error = generator.generate_music_from_prompt(user_input)

    if error:
        print(f"An error occurred: {error}")
    else:
        print("\n--- Successfully received data from Gemini ---")
        print(json.dumps(data, indent=2))
        print("\n---------------------------------------------")
