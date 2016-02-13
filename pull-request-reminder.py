import os
import requests
from github3 import login

POST_URL = 'https://slack.com/api/chat.postMessage'

IGNORE_WORDS = ['doppins']
SLACK_API_TOKEN = os.environ['SLACK_API_TOKEN']
GITHUB_API_TOKEN = os.environ['GITHUB_API_TOKEN']
ORGANIZATION = os.environ['ORGANIZATION']
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', '#general')

INITIAL_MESSAGE = """\
Hi! There's a few open pull requests you should take a \
look at:

"""


def check_repository(repository):
    return [pull for pull in repository.pull_requests()
            if pull.state == 'open']


def is_valid_title(title):
    lowercase_title = title.lower()
    for ignored_word in IGNORE_WORDS:
        if ignored_word.lower() in lowercase_title:
            return False

    return True


def format_pull_requests(pull_requests, owner, repository):
    lines = []

    for pull in pull_requests:
        if is_valid_title(pull.title):
            creator = pull.user.login
            line = '*[{0}/{1}]* <{2}|{3} - by {4}>'.format(
                owner, repository, pull.html_url, pull.title, creator)
            lines.append(line)

    return lines


def check_organization(organization_name):
    client = login(token=GITHUB_API_TOKEN)
    organization = client.organization(organization_name)
    lines = []

    for repository in organization.repositories():
        unchecked_pulls = check_repository(repository)
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

    response = requests.post(POST_URL, data=payload)
    answer = response.json()
    if not answer['ok']:
        raise Exception(answer['error'])


def main():
    lines = check_organization(ORGANIZATION)
    if lines:
        text = INITIAL_MESSAGE + '\n'.join(lines)
        send_to_slack(text)


main()
