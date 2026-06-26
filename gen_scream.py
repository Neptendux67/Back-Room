import wave
import struct
import math
import random

SAMPLE_RATE = 22050
DURATION = 2.5  # seconds
FILENAME = "assets/audio/monster-scream.wav"

samples = []
num_samples = int(SAMPLE_RATE * DURATION)

for i in range(num_samples):
    t = i / SAMPLE_RATE
    # Envelope: sharp attack, slow decay
    attack = min(1.0, t / 0.05)
    decay = max(0.0, 1.0 - (t / DURATION) ** 0.7)
    envelope = attack * decay

    # Base scream: mix of low growl and high shriek
    freq1 = 180 + math.sin(t * 8) * 60  # low growl oscillating
    freq2 = 900 + math.sin(t * 12) * 300  # high shriek
    freq3 = 450 + math.sin(t * 5) * 150  # mid range

    wave1 = math.sin(2 * math.pi * freq1 * t) * 0.4
    wave2 = math.sin(2 * math.pi * freq2 * t) * 0.3
    wave3 = math.sin(2 * math.pi * freq3 * t) * 0.2

    # Add distortion/noise for horror effect
    noise = (random.random() * 2 - 1) * 0.15
    
    # Combine
    sample = (wave1 + wave2 + wave3 + noise) * envelope * 0.8
    sample = max(-1.0, min(1.0, sample))
    samples.append(int(sample * 32767))

with wave.open(FILENAME, 'w') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(SAMPLE_RATE)
    f.writeframes(struct.pack(f'<{len(samples)}h', *samples))

print(f"Scream WAV generated: {FILENAME} ({len(samples)} samples, {DURATION}s)")
