# Vibe Tracker - AI Music Studio

Vibe Tracker is a terminal-based music creation tool that allows you to compose music in real-time using natural language commands, powered by Google's Gemini AI.

It features a persistent, callback-based audio engine for seamless, uninterrupted playback and live updates to the composition. You can add instruments, create patterns, and modify your track on the fly without ever stopping the music.

## Features

- **AI-Powered Composition**: Use natural language prompts (e.g., "add a funky bassline", "create a fast techno beat") to generate and modify music.
- **Real-Time Updates**: The music composition is updated live based on your commands without interrupting playback.
- **Seamless Looping**: A robust audio engine and carefully crafted AI prompts ensure patterns loop perfectly without clicks or pauses.
- **Text-Based Interface**: A clean, minimalist terminal UI built with Textual.
- **Extensible Synthesis**: Simple, classic synth waveforms (sine, square, saw, triangle) with ADSR envelope controls.

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

### 5. Get Your Google Gemini API Key

Vibe Tracker uses the Google Gemini API to understand your commands. The free tier is generous and perfect for this project.

1.  **Go to Google AI Studio**: Open your browser and navigate to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).
2.  **Create API Key**: You may be asked to log in with your Google account. Click on **"Create API key in new project"**.
3.  **Copy Your Key**: A new API key will be generated for you. Copy this key immediately and store it somewhere safe. This is your secret key.

### 6. Configure Your API Key

The application loads the API key from a `.env` file in the project's root directory.

1.  Create a new file named `.env` in the root of the `vibe-tracker` directory.
2.  Add the following line to the file, replacing `YOUR_API_KEY_HERE` with the key you just copied:

    ```
    GOOGLE_API_KEY='YOUR_API_KEY_HERE'
    ```

## Usage

Once everything is installed and configured, you can run the application:

```bash
python3 -m src.tui
```

The terminal interface will launch. Simply type a command into the input box at the bottom and press Enter.

### Example Commands

- `a simple 4/4 kick drum`
- `add a snare on beats 2 and 4`
- `create a fast, aggressive techno beat`
- `make the bpm 140`
- `delete track 1`

Enjoy creating music with AI!
