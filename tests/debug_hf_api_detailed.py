#!/usr/bin/env python3
"""
Detailed Hugging Face API debugging script
Analyzes raw API responses to diagnose None content issues
"""

import os
import sys
import json
from pathlib import Path
from openai import OpenAI

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def debug_hf_api_call(prompt: str, context: dict = None):
    """Make a direct HF API call with detailed logging"""
    print(f"\n{'='*60}")
    print(f"DEBUGGING HF API CALL: '{prompt}'")
    print(f"{'='*60}")
    
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("❌ HF_TOKEN not found")
        return
    
    model_name = os.getenv("HF_MODEL", "openai/gpt-oss-20b")
    print(f"Using model: {model_name}")
    print(f"Token: {hf_token[:8]}...")
    
    # Initialize client
    client = OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=hf_token
    )
    
    # Prepare messages
    system_prompt = """You are an expert AI music composer. Generate music compositions in JSON format.

IMPORTANT: Respond with ONLY a valid JSON object. No explanatory text or markdown.

Musical Rules:
1. Pattern Length: All patterns must be exactly 64 steps long (0-63)
2. Seamless Looping: Place notes near end (steps 60-63) for smooth transitions  
3. Density: Fill patterns with musical content, avoid long silences
4. Note Duration: Use duration field (1 for short, 64 for sustained notes)

JSON Schema:
{
  "bpm": 120,
  "instruments": [
    {
      "name": "kick",
      "oscillators": [{"waveform": "sine", "amplitude": 1.0}],
      "envelope": {"attack": 0.01, "decay": 0.1, "sustain": 0.0, "release": 0.1},
      "filter_type": "lowpass",
      "filter_cutoff_hz": 1000,
      "filter_resonance_q": 0.7,
      "effects": []
    }
  ],
  "tracks": [
    {
      "instrument_id": "kick",
      "pattern": {
        "length": 64,
        "notes": [{"step": 0, "note": 36, "velocity": 1.0, "duration": 1}]
      }
    }
  ]
}"""
    
    messages = [{"role": "system", "content": system_prompt}]
    
    if context:
        context_json = json.dumps(context, indent=2)
        messages.append({
            "role": "user",
            "content": f"Here is the current composition:\n\n```json\n{context_json}\n```"
        })
    
    messages.append({"role": "user", "content": f"User request: '{prompt}'"})
    
    print(f"\nRequest details:")
    print(f"  Messages count: {len(messages)}")
    print(f"  System prompt length: {len(system_prompt)}")
    print(f"  User prompt: '{prompt}'")
    
    try:
        print(f"\n🔄 Making API call...")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        print(f"✅ API call successful")
        
        # Detailed response analysis
        print(f"\n📊 RESPONSE ANALYSIS:")
        print(f"  Response type: {type(response)}")
        print(f"  Response object: {response}")
        
        # Check choices
        if hasattr(response, 'choices'):
            print(f"  Choices count: {len(response.choices)}")
            
            if response.choices:
                first_choice = response.choices[0]
                print(f"  First choice type: {type(first_choice)}")
                print(f"  First choice: {first_choice}")
                
                # Check message
                if hasattr(first_choice, 'message'):
                    message = first_choice.message
                    print(f"  Message type: {type(message)}")
                    print(f"  Message: {message}")
                    
                    # Check content
                    if hasattr(message, 'content'):
                        content = message.content
                        print(f"  Content type: {type(content)}")
                        print(f"  Content is None: {content is None}")
                        
                        if content is not None:
                            print(f"  Content length: {len(content)}")
                            print(f"  Content preview: {content[:200]}...")
                            
                            # Try to parse JSON
                            try:
                                parsed = json.loads(content)
                                print(f"  ✅ JSON parsing successful")
                                print(f"  Parsed keys: {list(parsed.keys())}")
                                return content, None
                            except json.JSONDecodeError as e:
                                print(f"  ❌ JSON parsing failed: {e}")
                                return content, str(e)
                        else:
                            print(f"  ❌ Content is None!")
                            return None, "Content is None"
                    else:
                        print(f"  ❌ Message has no content attribute")
                        return None, "No content attribute"
                else:
                    print(f"  ❌ Choice has no message attribute")
                    return None, "No message attribute"
            else:
                print(f"  ❌ No choices in response")
                return None, "No choices"
        else:
            print(f"  ❌ Response has no choices attribute")
            return None, "No choices attribute"
            
    except Exception as e:
        print(f"❌ API call failed: {e}")
        print(f"Exception type: {type(e)}")
        return None, str(e)

def test_problematic_prompts():
    """Test the specific prompts that are failing"""
    
    failing_prompts = [
        "add soft minor chord progression",
        "create a complex jazz chord progression with multiple instruments"
    ]
    
    working_prompts = [
        "create a simple kick drum",
        "add a snare drum with reverb"
    ]
    
    print("🔍 TESTING FAILING PROMPTS")
    print("=" * 60)
    
    for prompt in failing_prompts:
        content, error = debug_hf_api_call(prompt)
        
        if error:
            print(f"❌ FAILED: {error}")
        else:
            print(f"✅ SUCCESS: Got {len(content)} characters")
        
        print("-" * 40)
    
    print("\n🔍 TESTING WORKING PROMPTS (for comparison)")
    print("=" * 60)
    
    for prompt in working_prompts:
        content, error = debug_hf_api_call(prompt)
        
        if error:
            print(f"❌ FAILED: {error}")
        else:
            print(f"✅ SUCCESS: Got {len(content)} characters")
        
        print("-" * 40)

def test_with_context():
    """Test with existing composition context"""
    print("\n🔍 TESTING WITH CONTEXT")
    print("=" * 60)
    
    # Simple context
    context = {
        "bpm": 120,
        "instruments": [
            {
                "name": "kick",
                "oscillators": [{"waveform": "sine", "amplitude": 1.0}],
                "envelope": {"attack": 0.01, "decay": 0.1, "sustain": 0.0, "release": 0.1}
            }
        ],
        "tracks": [
            {
                "instrument_id": "kick",
                "pattern": {
                    "length": 64,
                    "notes": [{"step": 0, "note": 36, "velocity": 1.0, "duration": 1}]
                }
            }
        ]
    }
    
    content, error = debug_hf_api_call("add soft minor chord progression", context)
    
    if error:
        print(f"❌ FAILED WITH CONTEXT: {error}")
    else:
        print(f"✅ SUCCESS WITH CONTEXT: Got {len(content)} characters")

def main():
    """Run all debugging tests"""
    print("🚀 HUGGING FACE API DETAILED DEBUGGING")
    print("=" * 60)
    
    # Load .env file manually
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"\'')
    
    # Check environment
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("❌ HF_TOKEN not found. Please set it in .env file")
        print(f"Looking for .env at: {env_file}")
        print(f".env exists: {env_file.exists()}")
        return
    
    print(f"Environment OK - Token: {hf_token[:8]}...")
    
    # Test problematic prompts
    test_problematic_prompts()
    
    # Test with context
    test_with_context()
    
    print(f"\n📋 DEBUGGING COMPLETE")
    print("Check the detailed logs above to identify the root cause.")

if __name__ == "__main__":
    main()
