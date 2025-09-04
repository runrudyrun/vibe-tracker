# Vibe Tracker - AI Music Studio

Vibe Tracker is a terminal-based music creation tool that allows you to compose music in real-time using natural language commands, powered by multiple AI providers including GPT-OSS and Google's Gemini AI (and pretty much any model via HuggingFace or OpenRouter)

It features a persistent, callback-based audio engine for seamless, uninterrupted playback and live updates to the composition. You can add instruments, create patterns, and modify your track on the fly without ever stopping the music.

## Demo
[![Demo Video](https://img.youtube.com/vi/lUKt5bnnmFk/0.jpg)](https://www.youtube.com/watch?v=lUKt5bnnmFk)

## Features

- **AI-Powered Composition**: Use natural language prompts (e.g., "add a funky bassline", "create a fast techno beat") to generate and modify music.
- **Multiple AI Providers**: Support different models via Hugging Face, OpenRouter, and Google Gemini with automatic provider selection.
- **Real-Time Updates**: The music composition is updated live based on your commands without interrupting playback.
- **Seamless Looping**: A robust audio engine and carefully crafted AI prompts ensure patterns loop perfectly without clicks or pauses.
- **Text-Based Interface**: A clean, minimalist terminal UI built with Textual.
- **Extensible Synthesis**: Simple, classic synth waveforms (sine, square, saw, triangle) with ADSR envelope controls.
- **Built-in Effects**: Instrument-level reverb effects with configurable parameters.
- **Pattern Management**: Save and load patterns, export compositions to WAV files.

## Installation

Follow these steps to get Vibe Tracker running on your local machine.

### 1. Prerequisites

- Python 3.8 or newer.
- `portaudio` library for audio playback. 

  - On Debian/Ubuntu: `sudo apt-get install portaudio19-dev`
  - On macOS (using Homebrew): `brew install portaudio`
  - On other systems, please refer to the PortAudio documentation.

### 2. Clone the Repository

```bash
git clone https://github.com/your-username/vibe-tracker.git
cd vibe-tracker
```

### 3. Set Up a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

Install all the required Python packages using `pip`:

```bash
pip install -r requirements.txt
```

### 5. Configure AI Provider

Vibe Tracker supports multiple AI providers. You need to configure at least one:

#### Option A: Hugging Face GPT-OSS (Recommended)

1. **Get Hugging Face Token**: Go to [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. **Create Token**: Click "Create new token" with `inference.serverless.write` permissions
3. **Copy Token**: Save the token securely

#### Option B: OpenRouter (Flexible Model Access)

1. **Get OpenRouter API Key**: Go to [https://openrouter.ai/keys](https://openrouter.ai/keys)
2. **Create API Key**: Click "Create Key" and copy the key
3. **Choose Model**: Browse available models at [https://openrouter.ai/models](https://openrouter.ai/models)
4. **Optional - Provider Routing**: For consistent performance, choose a specific provider from [https://openrouter.ai/openai/gpt-oss-120b/providers](https://openrouter.ai/openai/gpt-oss-120b/providers)

#### Option C: Google Gemini

1. **Go to Google AI Studio**: Navigate to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. **Create API Key**: Click "Create API key in new project"
3. **Copy Key**: Save the API key securely

### 6. Environment Configuration

Create a `.env` file in the project root with your chosen provider:

```bash
LLM_PROVIDER=you_preferred_provider_here # auto, huggingface, openrouter, gemini

# For Hugging Face
HF_TOKEN=hf_your_token_here

# Optional: specify model (default: openai/gpt-oss-20b)
HF_MODEL=openai/gpt-oss-20b

# For OpenRouter (fallback)
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=openai/gpt-oss-120b
OPENROUTER_PROVIDER=wandb

# For Google Gemini (generous free tier)
GOOGLE_API_KEY=your_api_key_here
GOOGLE_MODEL=gemini-2.5-flash

# Optional: force specific provider (auto, huggingface, openrouter, gemini)
LLM_PROVIDER=auto
```

**Provider Selection Priority:**
0. According to LLM_PROVIDER variable (if it is set)
1. Hugging Face GPT-OSS (if `HF_TOKEN` is set)
2. OpenRouter (if `OPENROUTER_API_KEY` is set)
3. Google Gemini (if `GOOGLE_API_KEY` is set)
4. Error if neither is configured

## Usage

Once everything is installed and configured, you can run the application:

```bash
python3 -m src.tui
```

The terminal interface will launch. Simply type a command into the input box at the bottom and press Enter.

### Example Commands

- `a simple 4/4 kick drum`
- `add a snare on beats 2 and 4`
- `create a fast, aggressive techno beat with reverb`
- `make the bpm 140`
- `add a dreamy ambient pad with lots of reverb`
- `create a bass line that follows the kick`

### Keyboard Shortcuts

- **Space**: Play/Pause
- **Ctrl+S**: Save pattern
- **Ctrl+L**: Load pattern
- **Ctrl+E**: Export to WAV
- **Ctrl+X**: Clear entire project
- **Ctrl+D**: Delete track by index
- **Ctrl+Q**: Quit application

## Tutorials

### [Dub Music Production Guide](docs/dub-music-tutorial.md)
Learn to create music with step-by-step prompts on the dub music example Covers:
- Foundation rhythms (bass + kick)
- Characteristic dub snare with heavy reverb
- Atmospheric pads and minimal percussion
- Lead elements and classic dub techniques

## AI Providers Comparison

| Feature | Hugging Face GPT-OSS | OpenRouter | Google Gemini |
|---------|---------------------|------------|---------------|
| **Setup Time** | Instant | Instant | Instant |
| **Cost** | Monthly free quota, then pay-per-use (~$0.005/composition) | Daily free quota, then flexible pricing | Free tier available |
| **Speed** | 2-15 seconds | 3-8 seconds | 3-8 seconds |
| **Quality** | Good with specific, concise prompts | Best with specific, concise prompts | Creative and contextual |
| **JSON Consistency** | Requires provider selection for reliability | Requires provider selection for reliability | Most consistent JSON output |
| **Music Understanding** | Good | Good | Excellent |
| **Reliability** | Reliable when provider is fixed | Reliable when provider is fixed | Consistently reliable |

**Recommendation**: For GPT-OSS in HuggingFace and OpenRouter, select a specific provider and fix it using `OPENROUTER_PROVIDER` or `HF_PROVIDER` environment variable for consistent results.

## Effects System

Vibe Tracker includes a built-in effects system with instrument-level processing:

### Reverb Effect
- **room_size** (0.0-1.0): Controls reverb size and decay
- **damping** (0.0-1.0): High-frequency damping for natural sound
- **wet_level** (0.0-1.0): Reverb signal level
- **dry_level** (0.0-1.0): Original signal level
- **enabled** (true/false): Effect on/off switch

### Usage Examples
- "create a pad with cathedral reverb"
- "add a drum with tight room reverb"
- "make a dreamy ambient texture with lots of reverb"

## Performance Optimization

Vibe Tracker is optimized for real-time audio performance:
- **Vectorized Audio Processing**: 5-8x faster sample generation
- **Minimal Logging**: No debug output in audio callbacks
- **Efficient Effects**: <2ms processing time per buffer
- **Memory Management**: Reused buffers, minimal allocations

## Troubleshooting

### Audio Issues
- **No sound**: Check PortAudio installation and audio device
- **Crackling/dropouts**: Increase buffer size or reduce CPU load
- **High latency**: Use ASIO drivers on Windows, lower buffer size

### AI Provider Issues
- **Authentication errors**: Verify API tokens in `.env` file
- **Rate limits**: Wait or upgrade to paid tier
- **Model not found**: Check model name and provider availability
- **Timeout errors**: Try different provider or simpler prompts

### General Issues
- **Import errors**: Ensure all dependencies installed with `pip install -r requirements.txt`
- **Permission errors**: Check file permissions for patterns directory
- **Memory issues**: Close other applications, use smaller compositions

## Development

### Project Structure
```
vibe-tracker/
├── src/
│   ├── tui.py              # Terminal user interface
│   ├── llm_generator.py    # AI provider integration
│   ├── synthesis.py        # Audio synthesis engine
│   ├── sequencer.py        # Real-time audio sequencer
│   ├── effects.py          # Audio effects system
│   └── ...
├── tests/                  # Test suites
├── patterns/               # Saved patterns
└── scripts/                # Setup and utility scripts
```

### Running Tests
```bash
# Test Hugging Face integration
python tests/test_huggingface_integration.py

# Test effects system
python tests/test_effects_integration.py

# Test audio performance
python tests/debug_multitrack.py
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

Enjoy creating music with AI! 🎵
