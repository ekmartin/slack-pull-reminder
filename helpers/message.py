import requests
from logger import logger
from config import (SLACK_CHANNEL, SLACK_API_TOKEN)

POST_URL = 'https://slack.com/api/chat.postMessage'

def send_to_slack_channel(text, channel):
    """
    this method post message to slack channel
    """
    payload = {
        'token': SLACK_API_TOKEN,
        'channel': channel,
        'username': 'Pull Request Reminder',
        'icon_emoji': ':bell:',
        'mrkdwn': True,
        'text': text
    }
    logger.info(payload)

    response = requests.post(POST_URL, data=payload)
    answer = response.json()
    if not answer['ok']:
        raise Exception(answer['error'])


def send_to_slack_user(text, slack_user):
    payload = {
        'token': SLACK_API_TOKEN,
        'channel': slack_user,
        'username': 'Pull Request Reminder',
        'icon_emoji': ':bell:',
        'mrkdwn': True,
        'text': text
    }
    logger.info(payload)

    response = requests.post(POST_URL, data=payload)
    answer = response.json()
    if not answer['ok']:
        raise Exception(answer['error'])
