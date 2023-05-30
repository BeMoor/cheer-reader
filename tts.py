""" TTS message parsing and ElevenLabs API calling """
# pylint: disable=import-error
import pathlib
import os
from datetime import datetime
import logging
import time
import winsound
import requests
import librosa
from pydub import AudioSegment
import keyboard
import dotenv
from audio_adjustment import adjust_audio_speed
import cheerparser
from voices import VOICE_ALIAS_2_VOICE_ID
dotenv.load_dotenv()
logging.basicConfig(filename='logging_tts.txt', level=logging.DEBUG)

API_KEY = os.environ['ELEVENLABS_API_KEY']
BASE_URL = 'https://beta.elevenlabs.io/v1'

STABILITY = 0.65
SIMILARITY_BOOST = 0.85
SAVE_DIR = 'audio'


def get_tts_data(voice_id, text):
    headers = {
        'accept': 'audio/mpeg',
        'xi-api-key': API_KEY,
        'Content-Type': 'application/json',
    }
    json_data = {
        'text': text,
        'voice_settings': {
            'stability': f'{STABILITY}',
            'similarity_boost': f'{SIMILARITY_BOOST}',
        },
    }
    response = requests.post(
        f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
        headers=headers,
        json=json_data
    )
    if response.ok:
        return response.content
    logging.debug('ERROR in response data')
    logging.debug(response.status_code)
    logging.debug(response.text)
    return None


def _get_datestamp():
    datestamp = str(datetime.now())
    datestamp, dec = datestamp.split('.')
    datestamp = datestamp.replace(':', '_').replace(' ', '__')
    dec = dec[:3]
    datestamp += f'_{dec}'
    return datestamp


# pylint: disable=bare-except
def save_tts_data(tts_id, idx, voice_alias, data):
    try:
        if data is None:
            print('No data to save')
            return None
        datestamp = _get_datestamp()
        save_path = f"{SAVE_DIR}/{datestamp}_{tts_id}_{idx}_{voice_alias}.wav"
        if not os.path.exists(SAVE_DIR):
            os.mkdir(SAVE_DIR)

        with open(save_path, 'wb') as file:
            file.write(data)
        # export audio explicitly to WAV format
        seg = AudioSegment.from_file(save_path)
        seg.export(save_path, format='wav')

        # post-processing
        if voice_alias == 'dwight':
            adjust_audio_speed(save_path, 0.95)
        return save_path
    except:
        return None


def combine_audio(files):
    print('combine_audio files:', files)
    if len(files) == 1:
        segments = [AudioSegment.from_file(file=files[0])]
    else:
        segments = []
        for i, file in enumerate(files):
            file = file.replace('\\', '/')
            seg = AudioSegment.from_file(file=file) + os.environ['AUDIO_INCREASE']
            if 'dwight' in file:
                # need to boost dwight's audio
                seg += 8
            segments.append(seg)

            # if there's another file to include after this one, insert some silence as a buffer
            if i+1 < len(files):
                segments.append(AudioSegment.silent(duration=600))
    # segments = [AudioSegment.from_file(file.replace('\\','/')) for file in files]
    if not segments:
        print('No audio segments available.')
        return None
    result = segments[0]
    for seg in segments[1:]:
        result += seg
    return result


# character limits are imposed per donation, which may contain multiple prompts
def get_text_allowance(text, bits, prior_chars, bypass=False):
    if bypass:
        return text
    chars_per_extra_bit = int(os.environ['EXTRA_CHARS_PER_BIT'])
    base_cap = int(os.environ['MAX_CHARS'])
    threshold = int(os.environ['BIT_THRESHOLD'])\

    char_cap = base_cap + ((int(bits) - threshold)*chars_per_extra_bit) - prior_chars
    allowed_text = text[:char_cap]
    return allowed_text


# pylint: disable=too-many-arguments
def process_prompt(prompt, tts_id='', idx=0, prompt_id='1', bits=0, prior_chars=0, bypass=False):
    voice_alias, text = prompt
    # print('Prompt:', prompt)
    text = get_text_allowance(text, bits=bits, prior_chars=prior_chars, bypass=bypass)
    if len(text) == 0:
        return {}

    voice_id = VOICE_ALIAS_2_VOICE_ID[voice_alias]
    response_data = get_tts_data(voice_id=voice_id, text=text)
    file = save_tts_data(tts_id, idx, voice_alias, response_data)
    filepath = pathlib.Path(file)
    abspath = filepath.absolute()
    # print(abspath)

    result = {
        'id': prompt_id,
        'voice': {
            'id': voice_id,
            'alias': voice_alias
        },
        'file': str(abspath),
        'time': str(datetime.now())
    }
    return result


# pylint: disable=unexpected-keyword-arg
def play_sound(path):
    complete = False
    playing = False
    # audio duration in seconds, compare this to play time to mark completion
    duration = librosa.get_duration(path=path)
    start = time.time()
    while not complete:
        if not playing:
            # print('Starting')
            winsound.PlaySound(path, winsound.SND_ASYNC)
            playing = True
        if keyboard.is_pressed('space+t'):
            # print('Canceling')
            winsound.PlaySound(None, winsound.SND_PURGE)
            complete = True
        runtime = time.time() - start
        if runtime > duration or runtime > 60:
            complete = True
        time.sleep(0.05)


def process_prompts(prompts, tts_id='1', bits=None, bypass=False):
    results = []
    # process each pair of [<voice>, <text>]
    for i, prompt in enumerate(prompts):
        logging.debug('%s::::%s::::%s', tts_id, i, prompt)
        result = process_prompt(prompt, tts_id=tts_id, idx=i, bits=bits, bypass=bypass)
        if result:
            results.append(result)

    # combine each prompt's file into a single audio file for the whole message
    files = [result['file'] for result in results]

    combined_audio = combine_audio(files)

    save_path = f"{SAVE_DIR}/{_get_datestamp()}_{tts_id}.wav"
    combined_audio.export(save_path, format='wav')
    play_sound(save_path)
    filename = save_path.replace('\\', '/').split('/')[-1]
    return filename


def process_cheer_text(message, tts_id='1', bits=None, bypass=False):
    prompts = cheerparser.get_tts_voice_prompts(message)
    filename = process_prompts(prompts, tts_id=tts_id, bits=bits, bypass=bypass)
    logging.debug(filename)
    return filename
