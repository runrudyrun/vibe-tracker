import os
import google.generativeai as genai
import json
from openai import OpenAI


def _load_prompt(file_path: str) -> str:
    """Loads a prompt from a file, searching from the project root."""
    try:
        # Assuming the script is run from the project root, or a path relative to it
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback for when script is run from a different directory (like src/)
        try:
            # Get the directory of the current script (__file__)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level to the project root
            project_root = os.path.dirname(script_dir)
            # Construct the full path from the project root
            full_path = os.path.join(project_root, file_path)
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            # If it still fails, raise a more informative error
            raise IOError(f"Prompt file not found. Searched at '{file_path}' and '{full_path}'")

class LLMGenerator:
    def __init__(self, provider="auto"):
        self.provider = provider
        self.client = None
        self.model = None
        self.model_name = None
        self.gemini_prompt = _load_prompt('prompts/gemini_system_prompt.txt')
        self.gpt_oss_prompt = _load_prompt('prompts/gpt_oss_system_prompt.txt')
        
        # Check for explicit provider override first
        llm_provider_override = os.getenv("LLM_PROVIDER")
        if llm_provider_override:
            self.provider = llm_provider_override.lower()
        elif provider == "auto":
            # Auto-select provider based on available credentials
            if os.getenv("OPENROUTER_API_KEY"):
                self.provider = "openrouter"
            elif os.getenv("HF_TOKEN"):
                self.provider = "huggingface"
            elif os.getenv("GOOGLE_API_KEY"):
                self.provider = "gemini"
            else:
                raise ValueError("No LLM provider credentials found. Set OPENROUTER_API_KEY, HF_TOKEN, or GOOGLE_API_KEY")

        # Initialize the selected provider
        if self.provider == "openrouter":
            self._init_openrouter()
        elif self.provider == "huggingface":
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
            system_instruction=self.gemini_prompt
        )
        print(f"[LLM Generator] Using Gemini: {self.model_name}")

    def _init_openrouter(self):
        """Initialize OpenRouter provider"""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model_name = os.getenv("OPENROUTER_MODEL", "gryphe/mythomax-l2-13b")
        print(f"[LLM Generator] Using OpenRouter: {self.model_name}")

    def generate_music_from_prompt(self, user_prompt: str, context_composition: dict = None):
        """Generate music data from a user prompt with optional context
        Returns: (music_data, error, raw_response)
        """
        if self.provider == "openrouter":
            return self._generate_openrouter(user_prompt, context_composition)
        elif self.provider == "huggingface":
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
                {"role": "system", "content": self._get_gpt_oss_system_prompt()}
            ]
            
            if context_composition:
                context_json = json.dumps(context_composition, indent=2)
                messages.append({
                    "role": "user",
                    "content": f"""Here is the current composition:\n\n```json\n{context_json}\n```\n\nUser request: '{user_prompt}'"""
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"User request: '{user_prompt}'"
                })
            
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

    def _generate_openrouter(self, user_prompt: str, context_composition: dict = None):
        """Generate using OpenRouter API
        Returns: (music_data, error, raw_response)
        """
        raw_response = None
        try:
            messages = [
                {"role": "system", "content": self._get_gpt_oss_system_prompt()} # Reusing prompt as it's generic
            ]

            if context_composition:
                context_json = json.dumps(context_composition, indent=2)
                messages.append({
                    "role": "user",
                    "content": f"""Here is the current composition:\n\n```json\n{context_json}\n```\n\nUser request: '{user_prompt}'"""
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"User request: '{user_prompt}'"
                })

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=4096,
                temperature=0.7,
                response_format={"type": "json_object"},
                extra_body={
                    "provider": {
                        "order": [os.getenv("OPENROUTER_PROVIDER")],
                        "allow_fallbacks": False
                    }
                }
            )

            if not response.choices:
                error_msg = "OpenRouter API returned no choices"
                print(f"[LLM Generator] {error_msg}")
                return None, error_msg, None

            raw_response = response.choices[0].message.content

            if raw_response is None:
                error_msg = "OpenRouter API returned None content"
                print(f"[LLM Generator] {error_msg}")
                return None, error_msg, None

            try:
                music_data = json.loads(raw_response)
                return music_data, None, raw_response
            except json.JSONDecodeError as json_err:
                error_msg = f"JSON parsing failed: {json_err}"
                print(f"[LLM Generator] {error_msg}")
                return None, error_msg, raw_response

        except Exception as e:
            error_msg = str(e)
            print(f"[LLM Generator] OpenRouter Error: {error_msg}")
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
    
    def _get_gpt_oss_system_prompt(self):
        """Get system prompt optimized for GPT-OSS/Hugging Face API"""
        return self.gpt_oss_prompt
    
    def get_provider_info(self):
        """Get information about the current provider"""
        if self.provider == "openrouter":
            return f"OpenRouter ({self.model_name})"
        elif self.provider == "huggingface":
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
        print("\nTo use OpenRouter: Get key from https://openrouter.ai/keys")
        print("Then set: export OPENROUTER_API_KEY=your_key_here")
        print("You can also set OPENROUTER_MODEL to your model of choice.")
        print("\nTo use Hugging Face: Get token from https://huggingface.co/settings/tokens")
        print("Then set: export HF_TOKEN=your_token_here")
        print("\nTo use Gemini: Set GOOGLE_API_KEY in your .env file")
