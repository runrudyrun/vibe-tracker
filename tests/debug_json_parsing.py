#!/usr/bin/env python3
"""
Debug script to diagnose JSON parsing errors in LLM responses
Specifically targeting the "Expecting ',' delimiter: line (char 3143)" error
"""

import os
import sys
import json
import re
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from llm_generator import LLMGenerator

def analyze_json_error(raw_response: str, error: str):
    """Analyze JSON parsing error and provide detailed diagnostics"""
    print(f"=== JSON ERROR ANALYSIS ===")
    print(f"Error: {error}")
    print(f"Response length: {len(raw_response)} characters")
    
    # Extract character position from error message
    char_match = re.search(r'char (\d+)', error)
    if char_match:
        error_pos = int(char_match.group(1))
        print(f"Error position: character {error_pos}")
        
        # Show context around error position
        start = max(0, error_pos - 100)
        end = min(len(raw_response), error_pos + 100)
        context = raw_response[start:end]
        
        print(f"\nContext around error (chars {start}-{end}):")
        print("=" * 50)
        print(context)
        print("=" * 50)
        
        # Highlight the exact error character
        if error_pos < len(raw_response):
            error_char = raw_response[error_pos]
            print(f"Character at error position: '{error_char}' (ASCII: {ord(error_char)})")
        
        # Show line number
        lines_before_error = raw_response[:error_pos].count('\n')
        print(f"Line number: {lines_before_error + 1}")
        
        # Show the problematic line
        lines = raw_response.split('\n')
        if lines_before_error < len(lines):
            problematic_line = lines[lines_before_error]
            print(f"Problematic line: '{problematic_line}'")
    
    # Check for common JSON issues
    print(f"\n=== COMMON JSON ISSUES CHECK ===")
    
    # Check for trailing commas
    trailing_commas = re.findall(r',\s*[}\]]', raw_response)
    if trailing_commas:
        print(f"❌ Found {len(trailing_commas)} trailing commas: {trailing_commas[:3]}")
    else:
        print("✅ No trailing commas found")
    
    # Check for unescaped quotes
    unescaped_quotes = re.findall(r'(?<!\\)"(?![,}\]\s])', raw_response)
    if len(unescaped_quotes) > 20:  # Rough heuristic
        print(f"⚠️  Potentially unescaped quotes found: {len(unescaped_quotes)}")
    else:
        print("✅ Quote escaping looks OK")
    
    # Check bracket balance
    open_braces = raw_response.count('{')
    close_braces = raw_response.count('}')
    open_brackets = raw_response.count('[')
    close_brackets = raw_response.count(']')
    
    print(f"Bracket balance:")
    print(f"  Braces: {open_braces} open, {close_braces} close ({'✅' if open_braces == close_braces else '❌'})")
    print(f"  Brackets: {open_brackets} open, {close_brackets} close ({'✅' if open_brackets == close_brackets else '❌'})")
    
    # Check for control characters
    control_chars = [c for c in raw_response if ord(c) < 32 and c not in '\n\r\t']
    if control_chars:
        print(f"❌ Found {len(control_chars)} control characters: {[ord(c) for c in control_chars[:5]]}")
    else:
        print("✅ No problematic control characters")

def attempt_json_fixes(raw_response: str):
    """Try common fixes for JSON parsing issues"""
    print(f"\n=== ATTEMPTING JSON FIXES ===")
    
    fixes_tried = []
    
    # Fix 1: Remove trailing commas
    fixed_response = re.sub(r',(\s*[}\]])', r'\1', raw_response)
    if fixed_response != raw_response:
        fixes_tried.append("Removed trailing commas")
        try:
            json.loads(fixed_response)
            print("✅ Fix 1 SUCCESS: Removing trailing commas fixed the JSON")
            return fixed_response, fixes_tried
        except json.JSONDecodeError as e:
            print(f"❌ Fix 1 failed: {e}")
    
    # Fix 2: Remove markdown code blocks
    fixed_response = re.sub(r'```json\s*', '', fixed_response)
    fixed_response = re.sub(r'\s*```', '', fixed_response)
    if "```" in raw_response:
        fixes_tried.append("Removed markdown code blocks")
        try:
            json.loads(fixed_response)
            print("✅ Fix 2 SUCCESS: Removing markdown fixed the JSON")
            return fixed_response, fixes_tried
        except json.JSONDecodeError as e:
            print(f"❌ Fix 2 failed: {e}")
    
    # Fix 3: Try to find valid JSON substring
    # Look for the main JSON object
    start_brace = fixed_response.find('{')
    if start_brace != -1:
        # Find matching closing brace
        brace_count = 0
        end_pos = start_brace
        for i, char in enumerate(fixed_response[start_brace:], start_brace):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i + 1
                    break
        
        if end_pos > start_brace:
            json_substring = fixed_response[start_brace:end_pos]
            fixes_tried.append("Extracted JSON substring")
            try:
                json.loads(json_substring)
                print("✅ Fix 3 SUCCESS: Extracted valid JSON substring")
                return json_substring, fixes_tried
            except json.JSONDecodeError as e:
                print(f"❌ Fix 3 failed: {e}")
    
    print("❌ All automatic fixes failed")
    return raw_response, fixes_tried

def test_specific_prompt(prompt: str):
    """Test a specific prompt and analyze any JSON errors"""
    print(f"\n{'='*60}")
    print(f"TESTING PROMPT: '{prompt}'")
    print(f"{'='*60}")
    
    try:
        generator = LLMGenerator()
        print(f"Using provider: {generator.get_provider_info()}")
        
        # Generate music
        music_data, error, raw_response = generator.generate_music_from_prompt(prompt)
        
        if error and "JSON parsing failed" in error:
            print(f"❌ JSON PARSING ERROR DETECTED")
            
            # Save raw response for analysis
            with open("debug_raw_response.txt", "w", encoding="utf-8") as f:
                f.write(raw_response)
            print(f"Raw response saved to debug_raw_response.txt")
            
            # Analyze the error
            analyze_json_error(raw_response, error)
            
            # Try fixes
            fixed_response, fixes = attempt_json_fixes(raw_response)
            
            if fixes:
                print(f"\nFixes applied: {', '.join(fixes)}")
                with open("debug_fixed_response.txt", "w", encoding="utf-8") as f:
                    f.write(fixed_response)
                print(f"Fixed response saved to debug_fixed_response.txt")
            
            return False, raw_response, error
            
        elif error:
            print(f"❌ OTHER ERROR: {error}")
            return False, raw_response, error
        else:
            print(f"✅ SUCCESS: Generated {len(music_data.get('tracks', []))} tracks")
            return True, raw_response, None
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False, None, str(e)

def main():
    """Run comprehensive JSON parsing diagnostics"""
    print("🔍 JSON PARSING DIAGNOSTICS")
    print("=" * 60)
    
    # Check environment
    hf_token = os.getenv("HF_TOKEN")
    gemini_key = os.getenv("GOOGLE_API_KEY")
    
    print(f"Environment:")
    print(f"  HF_TOKEN: {'✅ Set' if hf_token else '❌ Missing'}")
    print(f"  GOOGLE_API_KEY: {'✅ Set' if gemini_key else '❌ Missing'}")
    
    if not hf_token and not gemini_key:
        print("❌ No API keys configured. Please set HF_TOKEN or GOOGLE_API_KEY")
        return
    
    # Test prompts that might cause JSON issues
    test_prompts = [
        "add soft minor chord progression",  # The failing prompt from screenshot
        "create a simple kick drum",
        "add a snare drum with reverb",
        "create a complex jazz chord progression with multiple instruments",
        "make a long ambient pad with lots of effects and modulation",
    ]
    
    results = []
    
    for prompt in test_prompts:
        success, raw_response, error = test_specific_prompt(prompt)
        results.append({
            'prompt': prompt,
            'success': success,
            'error': error,
            'response_length': len(raw_response) if raw_response else 0
        })
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"Success rate: {successful}/{total} ({successful/total*100:.1f}%)")
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} '{result['prompt'][:40]}...' - {result.get('error', 'OK')}")
    
    # Recommendations
    print(f"\n📋 RECOMMENDATIONS:")
    
    failed_results = [r for r in results if not r['success']]
    if failed_results:
        json_errors = [r for r in failed_results if r['error'] and 'JSON parsing failed' in r['error']]
        if json_errors:
            print("1. JSON parsing issues detected - consider:")
            print("   - Improving system prompt to enforce valid JSON")
            print("   - Adding JSON validation/fixing in post-processing")
            print("   - Using response_format={'type': 'json_object'} more consistently")
        
        api_errors = [r for r in failed_results if r['error'] and 'JSON parsing failed' not in r['error']]
        if api_errors:
            print("2. API issues detected - consider:")
            print("   - Checking rate limits and quotas")
            print("   - Adding retry logic with exponential backoff")
            print("   - Implementing fallback between providers")
    else:
        print("✅ All tests passed! JSON parsing is working correctly.")

if __name__ == "__main__":
    main()
