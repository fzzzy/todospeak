import io
import numpy as np
from pydub import AudioSegment


def detect_silence(
    audio_data,
    sample_rate=48000,
    window_length=1,
    threshold=3e-3
):
    window_size = int(window_length * sample_rate)
    # 0.5 sec * 48k = 24k samples
    n_windows = len(audio_data) // window_size
        
    # Normalize
    audio_data = audio_data / 32767.0

    for i in range(n_windows):
        start = i * window_size
        end = (i + 1) * window_size

        rms = np.sqrt(np.mean(np.square(audio_data[start:end])))

        if rms < threshold:
            return (start, end)


def save_as_mp3(samples, sample_rate, filename):
    audio = AudioSegment(
        samples.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=1
    )
    f = io.BytesIO()
    f.name = "a.mp3"
    return audio.export(f, format="mp3")

