# Dub Music Production Tutorial

This tutorial will guide you through creating authentic dub music in Vibe Tracker using step-by-step prompts optimized for the GPT-OSS model.

## What is Dub Music?

Dub is a genre of electronic music that emerged from reggae in the 1970s. It's characterized by:
- Deep sub bass (40-80Hz)
- Sparse, syncopated drum patterns
- Heavy use of reverb and delay effects
- Filtered melodic elements
- Minimal but impactful arrangements
- Echo effects on percussion

## Step-by-Step Production Guide

### Phase 1: Foundation (Start Here)
Create the rhythmic foundation with bass and kick drum:

```
Create dub foundation at 75 BPM: deep sub bass using sine wave, sparse kick on steps 0,16,32,48, bass with lowpass filter 120Hz, resonance 0.7
```

**What this does:**
- Sets a classic dub tempo (75 BPM)
- Creates deep sub bass using pure sine wave
- Places kick drum on strong beats for foundation
- Applies lowpass filter to warm the bass

### Phase 2: Add Rhythm
Add the characteristic dub snare with heavy reverb:

```
Add dub snare with heavy reverb: triangle wave, reverb room_size 0.8 wet_level 0.7, hits on steps 8,24,40,56 plus ghost notes on 12,28
```

**What this does:**
- Uses triangle wave for punchy snare sound
- Applies heavy reverb (room_size 0.8, wet_level 0.7)
- Places snare on off-beats (classic dub pattern)
- Adds ghost notes for groove

### Phase 3: Atmospheric Pad
Create the atmospheric backdrop:

```
Add atmospheric pad: sawtooth+sine oscillators, lowpass filter 800Hz, light reverb room_size 0.4, sustained chords on steps 0,16,32 duration 32
```

**What this does:**
- Combines sawtooth and sine waves for rich texture
- Filters high frequencies for warmth
- Adds subtle reverb for space
- Creates sustained chords that evolve slowly

### Phase 4: Minimal Percussion
Add subtle hi-hat elements:

```
Add minimal hi-hats: noise wave, highpass filter 2000Hz, short hits on off-beats steps 4,12,20,28,36,44,52,60 duration 1
```

**What this does:**
- Uses noise wave for realistic hi-hat texture
- Highpass filter removes low frequencies
- Places hits on syncopated off-beats
- Short duration (1) for crisp percussive sound

### Phase 5: Lead Element
Add the final melodic element:

```
Add dub lead melody: square wave, bandpass filter 1200Hz resonance 1.2, reverb room_size 0.6, sparse notes on steps 2,18,34,50 duration 8
```

**What this does:**
- Square wave provides characteristic electronic sound
- Bandpass filter creates focused frequency range
- Medium reverb adds space without muddiness
- Sparse placement maintains dub minimalism

## Key Vibe Tracker Features for Dub

### Reverb Effects
Vibe Tracker's reverb system is perfect for dub:
- `room_size`: Controls reverb length (0.6-0.8 for dub)
- `wet_level`: Amount of reverb (0.5-0.8 for heavy dub reverb)
- `dry_level`: Original signal (usually 1.0)
- `damping`: High-frequency rolloff (0.3-0.5 for natural sound)

### Filter Types
- **Lowpass**: Warms bass and pads (120-800Hz)
- **Highpass**: Cleans hi-hats and percussion (2000Hz+)
- **Bandpass**: Focuses lead sounds (1000-1500Hz)

### Timing and Rhythm
Dub uses specific step patterns in the 64-step grid:
- **Kick**: Steps 0, 16, 32, 48 (on the 1)
- **Snare**: Steps 8, 24, 40, 56 (on the 3)
- **Hi-hats**: Off-beat syncopation
- **Bass**: Often sustained or on strong beats

## Pro Tips

### Prompt Formatting
- Keep prompts **under 50 words** for GPT-OSS efficiency
- Always specify **exact step numbers** for rhythm precision
- Include **filter frequencies** and **reverb parameters**
- Mention **duration** for sustained vs percussive sounds

### Building Your Track
1. **Start minimal** - dub is about space and atmosphere
2. **Build incrementally** - each prompt adds to existing composition
3. **Use the right BPM** - 70-85 BPM for authentic dub feel
4. **Layer effects** - reverb is essential for dub character

### Common Dub Chord Progressions
When adding harmonic content, try these classic progressions:
- Am - F - C - G (minor feel)
- Dm - Bb - F - C (deeper minor)
- Em - C - G - D (brighter feel)

## Troubleshooting

**If your bass is too muddy:**
- Lower the filter cutoff frequency
- Reduce reverb on bass elements
- Use highpass filter on other elements

**If the mix sounds empty:**
- Add more ghost notes to percussion
- Increase reverb wet levels
- Add subtle pad movements

**If it doesn't sound like dub:**
- Check your BPM (should be 70-85)
- Increase reverb on snare/percussion
- Make sure bass is deep and prominent
- Reduce note density - dub is minimal

## Next Steps

Once you've mastered basic dub production:
1. Experiment with different filter cutoff frequencies
2. Try varying reverb parameters between instruments
3. Add subtle automation by modifying existing tracks
4. Export your creations and layer them in external DAWs

Happy dubbing! 🎵
