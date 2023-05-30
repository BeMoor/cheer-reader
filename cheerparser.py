""" Tools for parsing comments to retrieve the voice TTS commands for the API """
from voices import VOICE_ALIAS_2_VOICE_ID


# checks text to see if it matches "<voice>:" structure and voice is found in VOICE_ALIASES
def _is_voice_indicator(token):
    return token.endswith(':') and f'{token[:-1].lower()}' in VOICE_ALIAS_2_VOICE_ID


def get_tts_voice_prompts(text: str) -> list:
    """
    Parses a cheer event message into a list of cheer prompts
    :param text: string -- message from event in subscription payload
    :return:
    """
    text = ' '.join(text.replace('\n', ' ').replace('\t', ' ').strip().split())
    tokens = text.split()
    # remove '11io' and 'cheer*' from text
    tokens = [
        t for t in tokens if not (
                len(t) > 5 and
                t.lower().startswith('cheer') and
                all(c.isdigit() for c in t[5:])
        ) and t.lower() != '11io'
    ]

    tts_commands = []
    voice = None
    voice_text = []

    for i, token in enumerate(tokens):
        if _is_voice_indicator(token.lower()):
            # process current voice and text
            if voice is not None:
                tts_commands.append([voice, ' '.join(voice_text)])
            # initialize new voice and text tracking
            voice = token.lower()[:-1]
            voice_text = []
        else:
            voice_text.append(token)

        # check at end of text
        if voice is not None and i == (len(tokens) - 1) and len(voice_text) > 0:
            tts_commands.append([voice.lower(), ' '.join(voice_text)])

    return tts_commands
