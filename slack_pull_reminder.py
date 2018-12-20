import os
import sys
import logging

import requests
from github3 import login

POST_URL = 'https://slack.com/api/chat.postMessage'

ignoreWords = os.environ.get('IGNORE_WORDS')
IGNORE_WORDS = [i.lower().strip() for i in ignoreWords.split(',')] if ignoreWords else []

ignoreLabels = os.environ.get('IGNORE_LABELS')
default_ignore_lables = ['wip']
IGNORE_LABELS = [i.lower().strip() for i in ignoreLabels.split(',')] if ignoreLabels else default_ignore_lables

repositories = os.environ.get('REPOSITORIES')
REPOSITORIES = [r.lower().strip() for r in repositories.split(',')] if repositories else []

usernames = os.environ.get('USERNAMES')
USERNAMES = [u.lower().strip() for u in usernames.split(',')] if usernames else []

SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', 'GEXT4PWUC')

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
logger = logging.getLogger(__name__)

try:
    SLACK_API_TOKEN = os.environ['SLACK_API_TOKEN']
    GITHUB_API_TOKEN = os.environ['GITHUB_API_TOKEN']
    ORGANIZATION = os.environ['ORGANIZATION']
    print('debug message')
    print(SLACK_API_TOKEN, GITHUB_API_TOKEN, ORGANIZATION)
except KeyError as error:
    sys.stderr.write('Please set the environment variable {0}'.format(error))
    sys.exit(1)

INITIAL_MESSAGE = """\
Hi! There's a few open pull requests you should take a \
look at:

"""


def fetch_repository_pulls(repository):
    pulls = []
    for pull in repository.pull_requests():
        if pull.state == 'open' and (not USERNAMES or pull.user.login.lower() in USERNAMES):
            print(pull,'== pull ====')
            pulls.append(pull)
    return pulls


def is_valid_pull(pull):
    if contains_ignore_word(pull.title):
        return False
    
    logger.info('pull #%s lables: %s', pull.number, pull.labels)
    labels = map(lambda item: item.get('name'), pull.labels)
    logger.debug('pull #%s has lables: %s', pull.number, labels)
    if contains_ignore_label(labels):
        return False

    return True


def contains_ignore_label(labels):
    for ignored_label in IGNORE_LABELS:
        if ignored_label in labels:
            return True
    return False

def contains_ignore_word(title):
    lowercase_title = title.lower()
    for ignored_word in IGNORE_WORDS:
        if ignored_word in lowercase_title:
            return True

    return False

def format_pull_requests(pull_requests, owner, repository):
    lines = []

    for pull in pull_requests:
        if is_valid_pull(pull):
            creator = pull.user.login
            prTitle = pull.title.encode('utf-8')
            line = '*[{0}/{1}]* <{2}|{3}> - by {4}'.format(
                owner, repository, pull.html_url, prTitle, creator)
            logger.info('pull: %s', pull)
            lines.append(line)

    return lines


def fetch_organization_pulls(organization_name):
    """
    Returns a formatted string list of open pull request messages.
    """
    client = login(token=GITHUB_API_TOKEN)
    organization = client.organization(organization_name)
    print(organization, organization_name)
    lines = []

    for repository in organization.repositories():
        if REPOSITORIES and repository.name.lower() not in REPOSITORIES:
            continue
        unchecked_pulls = fetch_repository_pulls(repository)
        lines += format_pull_requests(unchecked_pulls, organization_name,
                                      repository.name)

    return lines


def send_to_slack(text):
    payload = {
        'token': SLACK_API_TOKEN,
        'channel': SLACK_CHANNEL,
        'username': 'Pull Request Reminder',
        'icon_emoji': ':bell:',
        'text': text
    }
    logger.info(payload)

    response = requests.post(POST_URL, data=payload)
    answer = response.json()
    if not answer['ok']:
        raise Exception(answer['error'])


def cli():
    lines = fetch_organization_pulls(ORGANIZATION)
    if lines:
        text = INITIAL_MESSAGE + '\n'.join(lines)
        send_to_slack(text)

if __name__ == '__main__':
    cli()
