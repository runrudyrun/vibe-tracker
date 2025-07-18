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

You must respond with a single, valid JSON object representing the *complete, updated* composition. Do not respond with anything else.
The JSON structure must be:

{
  "bpm": <integer>,
  "instruments": [
    {
      "name": "<string>",
      "waveform": "<string, one of 'sine', 'square', 'sawtooth', 'triangle', 'noise'>",
      "attack": <float>,
      "decay": <float>,
      "sustain_level": <float>,
      "release": <float>
    }
  ],
  "tracks": [
    {
      "instrument_name": "<string>",
      "notes": [
        {"step": <integer>, "note": "<string>"}
      ]
    }
  ]
}
"""

class LLMGenerator:
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
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
