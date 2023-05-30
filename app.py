""" Main logic for Twitch App """
# pylint: disable=bare-except, unspecified-encoding
import uuid
from queue import Queue
import json
import os
import logging
import requests
import websocket

logging.basicConfig(filename='log_websocket.txt', level=logging.DEBUG)


def load_settings():
    try:
        with open('settings.txt', 'r') as file:
            lines = file.readlines()
        lines = [line.strip() for line in lines if line.strip() != '']
        for line in lines:
            option, value = line.split('=')
            os.environ.setdefault(option, value)
    except:
        pass


def _is_user_blacklisted(user):
    try:
        with open('user_blacklist.txt', 'r') as file:
            lines = file.readlines()
        lines = [line.strip().lower() for line in lines]
        return user in lines
    except:
        return False


def _should_read(event: dict, bit_threshold, indicator):
    bits = event['bits']
    message = event['message']
    sender = event['user_name'].lower()
    if _is_user_blacklisted(sender):
        return False, 'blacklist'
    if sender == 'bemoor' and indicator in message:
        return True, 'bemoor'
    sufficient_bits = bits >= bit_threshold
    has_indicator = indicator in message
    if not has_indicator:
        return False, 'missing indicator'
    if not sufficient_bits:
        return False, 'bit threshold not met'
    return True, 'bit threshold met and indicator found'


def _log_prompt_data(data, prompt_id):
    with open('data.txt', 'a') as file:
        file.write(f"{prompt_id}::::{str(data)}\n")


class CheerReader:
    # pylint: disable=too-many-instance-attributes, too-many-arguments
    def __init__(self, client_id, user_id, user_oauth, bit_threshold=100, indicator='11io'):
        self.client_id = client_id
        self.user_id = user_id
        self.user_oauth = user_oauth
        self.bit_threshold = bit_threshold
        self.indicator = indicator
        self.session_id = None
        self.app = websocket.WebSocketApp(
            url='wss://eventsub-beta.wss.twitch.tv/ws',
            on_message=self.on_message,
        )
        self.subscriptions = {}
        self.queue = Queue()

    def _process_event(self, json_data):
        load_settings()
        should_read, reason = _should_read(
            event=json_data['payload']['event'],
            bit_threshold=self.bit_threshold,
            indicator=self.indicator
        )
        if should_read:
            data = json_data['payload']['event']['message']
            bits = json_data['payload']['event']['bits']
            sender = json_data['payload']['event']['user_name'].lower()
            try:
                data = data.encode('latin', 'ignore').decode()
            except:
                data = str(data)
            logging.debug('Event Message:')
            logging.debug(data)
            prompt_id = uuid.uuid1()
            self.queue.put((prompt_id, data, bits, sender))
            _log_prompt_data(data, prompt_id=prompt_id)
        else:
            logging.debug('Should not read -- %s', reason)

    # pylint: disable='unused-argument
    def on_message(self, wsapp, message):
        """
        Processes incoming data from websocket connection.
        :param wsapp:
        :param message: json
        """
        logging.debug(message)
        json_data = json.loads(message)
        if self.session_id is None:  # move to "on_open()" ?
            logging.debug('Need to set session id')
            session_id = json_data['payload']['session']['id']
            logging.debug('Session ID from message: %s', session_id)
            self.session_id = session_id
            self.subscribe_to_bits()
        elif 'event' in json_data['payload']:
            self._process_event(json_data)

    def receive_test_event(self, json_data: dict):
        self._process_event(json_data)

    def subscribe_to_bits(self):
        if self.session_id is not None:
            headers = self.get_headers()
            condition = {
                "broadcaster_user_id": str(self.user_id),
            }
            transport = {
                "method": "websocket",
                "session_id": self.session_id,
            }
            message = {
                "type": "channel.cheer",
                "version": "1",
                "condition": condition,
                "transport": transport,
            }
            response = requests.post(
                url='https://api.twitch.tv/helix/eventsub/subscriptions',
                json=message,
                headers=headers,
                timeout=15
            )
            # print(response.content)
            subscription_result = json.loads(response.content)
            self.subscriptions[subscription_result['data'][0]['id']] = subscription_result

    def get_headers(self):
        headers = {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {self.user_oauth}'
        }
        return headers
