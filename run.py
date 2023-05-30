import os
import threading
from time import sleep
import dotenv
from app import CheerReader, load_settings
import tts
dotenv.load_dotenv()


load_settings()

CLIENT_ID = os.environ['CLIENT_ID']
AUTH_TOKEN = os.environ['AUTH_TOKEN']
CHANNEL_ID = os.environ['CHANNEL_ID']
BIT_THRESHOLD = int(os.environ['BIT_THRESHOLD'])
INDICATOR = os.environ['INDICATOR']
FREE_PASS_USERS = os.environ.get('FREE_PASS_USERS', 'bemoor').split(',')  # list of usernames which can cheer for 1 bit

APP = CheerReader(CLIENT_ID, CHANNEL_ID, AUTH_TOKEN, BIT_THRESHOLD, INDICATOR)


def process_queue():
    while True:
        task = APP.queue.get()
        if task:
            print('Task:', task)
            prompt_id, data, bits, sender = task
            bypass = sender == 'bemoor' or sender in FREE_PASS_USERS
            filename = tts.process_cheer_text(data, tts_id=prompt_id, bits=bits, bypass=bypass)
            APP.queue.task_done()
            print(f'Task completed: {filename}')
        sleep(0.1)


if __name__ == '__main__':
    t1 = threading.Thread(
        target=APP.app.run_forever,
        kwargs={'ping_interval': 60, 'ping_timeout': 10, 'reconnect': 60}
    )
    t2 = threading.Thread(
        target=process_queue
    )
    # TODO -- t2 currently does everything related to TTS, which includes parsing and elevenlabs API
    #  requests and audio playback, all in sequence per cheer. To avoid potential backlog issues,
    #  maybe it would be better to separate t2 into more process queues which individually handle:
    #  1) parsing and sending out API requests,
    #  2) retrieval of API requests and saving files,
    #  3) audio playback
    print('Starting App')
    t1.start()
    print('Starting Queue Processor')
    t2.start()
