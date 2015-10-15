import os
import requests
from github3 import login

POST_URL = 'https://slack.com/api/chat.postMessage'

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


def format_pull_requests(pull_requests, owner, repository):
    lines = []

    for pull in pull_requests:
        creator = pull.user.login
        line = '    *[{0}/{1}]* <{2}|{3} - by {4}>'.format(
            owner, repository, pull.html_url, pull.title, creator)
        lines.append(line)

    return lines


def check_organization(organization_name):
    client = login(token=GITHUB_API_TOKEN)
    organization = client.organization(organization_name)
    text = INITIAL_MESSAGE
    lines = []

    for repository in organization.repositories():
        unchecked_pulls = check_repository(repository)
        lines += format_pull_requests(unchecked_pulls, organization_name,
                                      repository.name)

    text += '\n'.join(lines)
    return text


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
    text = check_organization(ORGANIZATION)
    if text:
        send_to_slack(text)


main()
