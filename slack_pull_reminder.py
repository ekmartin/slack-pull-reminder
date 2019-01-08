import os
import sys
import requests
from github3 import login

from helpers.tools import (
    is_valid_pull,
    fetch_repository_pulls,
    get_review_contribution_section,
    get_open_pulls_section,
    get_reviewers_debt_section, 
)
from helpers.config import (
    REPOSITORIES,
    SLACK_API_TOKEN,
    SLACK_CHANNEL,
    ORGANIZATION,
    GITHUB_API_TOKEN,
    USERNAMES,
    LOGLEVEL,
)
from helpers.logger import logger

POST_URL = 'https://slack.com/api/chat.postMessage'

INITIAL_MESSAGE = """\
Hi! There's a few open pull requests you should take a \
look at:

"""

def get_organization_pulls(organization_name):
    unchecked_pulls = fetch_organization_pulls(organization_name)
    return list(filter(lambda pull: is_valid_pull(pull), unchecked_pulls))

"""
Returns a list of open pull request.
"""
def fetch_organization_pulls(organization_name):
    client = login(token=GITHUB_API_TOKEN)
    organization = client.organization(organization_name)
    pulls = []

    for repository in organization.repositories():
        if REPOSITORIES and repository.name.lower() not in REPOSITORIES:
            continue
        pulls += fetch_repository_pulls(repository)

    return pulls


def send_to_slack(text):
    payload = {
        'token': SLACK_API_TOKEN,
        'channel': SLACK_CHANNEL,
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

def get_bot_message():
    pulls = get_organization_pulls(ORGANIZATION)
    lines = []

    lines.append(get_open_pulls_section(pulls))
    lines.append(get_review_contribution_section(pulls, 7))
    lines.append(get_reviewers_debt_section(pulls))

    return '\n'.join(lines)


def cli():
    msg = get_bot_message()
    if msg:
        send_to_slack(msg)

if __name__ == '__main__':
    cli()
