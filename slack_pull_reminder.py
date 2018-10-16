import os
import sys

import requests
from github3 import login, pulls, repos

POST_URL = 'https://slack.com/api/chat.postMessage'

ignore = os.environ.get('IGNORE_WORDS')
IGNORE_WORDS = [i.lower().strip() for i in ignore.split(',')] if ignore else []

repositories = os.environ.get('REPOSITORIES')
REPOSITORIES = [r.lower().strip() for r in repositories.split(',')] if repositories else []

usernames = os.environ.get('USERNAMES')
USERNAMES = [u.lower().strip() for u in usernames.split(',')] if usernames else []

SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', '#general')

SHOW_BUILD_STATUS = os.environ.get('SHOW_BUILD_STATUS', True)
SUCCESS_EMOJI = os.environ.get('SUCCESS_EMOJI', u'✓')
PENDING_EMOJI = os.environ.get('PENDING_EMOJI', u'⟳')
FAILURE_EMOJI = os.environ.get('FAILURE_EMOJI', u'⨉')

state_to_emoji = {
    'success': SUCCESS_EMOJI,
    'pending': PENDING_EMOJI,
    'failure': FAILURE_EMOJI,
}

try:
    SLACK_API_TOKEN = os.environ['SLACK_API_TOKEN']
    GITHUB_API_TOKEN = os.environ['GITHUB_API_TOKEN']
    ORGANIZATION = os.environ['ORGANIZATION']
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
            pulls.append(pull)
    return pulls


def is_valid_title(title):
    lowercase_title = title.lower()
    for ignored_word in IGNORE_WORDS:
        if ignored_word in lowercase_title:
            return False

    return True


def get_combined_status(pull_request):
    """
    A fun hack :/ to get the combined status of a pull request. github3.py doesn't support this atm, so hack it in
    :param pull_request: github3.py PullRequest obj
    :return: github3.py CombinedStatus obj
    """
    combined_status_url = pull_request.statuses_url.replace('/statuses/', '/status/')
    json = pull_request._json(pull_request._get(combined_status_url), 200)
    return pull_request._instance_or_null(repos.status.CombinedStatus, json)


def format_pull_requests(pull_requests, owner, repository):
    lines = []

    for pull in pull_requests:
        if is_valid_title(pull.title):
            creator = pull.user.login
            combined_status = get_combined_status(pull)
            if SHOW_BUILD_STATUS and combined_status:
                build_status = state_to_emoji.get(combined_status.state, " ")
            else:
                build_status = ""
            line = '*{}[{}/{}]* <{}|{} - by {}>'.format(
                build_status, owner, repository, pull.html_url, pull.title, creator)
            lines.append(line)

    return lines


def fetch_organization_pulls(organization_name):
    """
    Returns a formatted string list of open pull request messages.
    """
    client = login(token=GITHUB_API_TOKEN)
    organization = client.organization(organization_name)
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
