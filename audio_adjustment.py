""" Functions for adjusting the downloaded audio files to fine-tune the sound """
import wave

# file = 'audio/123_0_dwight_2023-04-11__13_39_14_112.wav'  # testing
CHANNELS = 1
WIDTH = 2


# audio can be slowed down or sped up to make the voice sound deeper or higher
def adjust_audio_speed(filename, speed_multiplier):
    if speed_multiplier == 1.0:
        return filename  # no change
    spf = wave.open(filename, 'rb')
    framerate = spf.getframerate()
    signal = spf.readframes(-1)

    new_filename = filename.replace('.wav', '_slow.wav')
    new_file = wave.open(new_filename, 'wb')
    new_file.setnchannels(CHANNELS)
    new_file.setsampwidth(WIDTH)
    new_file.setframerate(framerate * speed_multiplier)
    new_file.writeframes(signal)
    new_file.close()
    return new_filename
