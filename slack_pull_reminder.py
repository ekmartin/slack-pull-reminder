import os
import sys

import requests
from github3 import login

POST_URL = 'https://slack.com/api/chat.postMessage'

ignore = os.environ.get('IGNORE_WORDS')
IGNORE_WORDS = [i.lower().strip() for i in ignore.split(',')] if ignore else []

repositories = os.environ.get('REPOSITORIES')
REPOSITORIES = [r.lower().strip() for r in repositories.split(',')] if repositories else []

usernames = os.environ.get('USERNAMES')
USERNAMES = [u.lower().strip() for u in usernames.split(',')] if usernames else []

teams = os.environ.get('TEAMS')
TEAMS = [t.lower().strip() for t in teams.split(',')] if teams else []

SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', '#general')

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


def get_teams(organization, team_names=None):
    if not team_names:
        return list(organization.teams())
    else:
        _teams = []
        for team in organization.teams():
            if team.name.lower() in TEAMS:
                _teams.append(team)
        return _teams


def get_team_member_usernames(team):
    return [member.login for member in team.members()]


def add_TEAMS_usernames_to_USERNAMES(organization):
    global USERNAMES
    _teams = get_teams(organization, TEAMS)
    _usernames = set(USERNAMES)
    for team in _teams:
        _usernames.update(get_team_member_usernames(team))
    USERNAMES = list(_usernames)


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


def format_pull_requests(pull_requests, owner, repository):
    lines = []

    for pull in pull_requests:
        if is_valid_title(pull.title):
            creator = pull.user.login
            line = '*[{0}/{1}]* <{2}|{3} - by {4}>'.format(
                owner, repository, pull.html_url, pull.title, creator)
            lines.append(line)

    return lines

def get_organization(organization_name):
    client = login(token=GITHUB_API_TOKEN)
    return client.organization(organization_name)


def fetch_organization_pulls(organization):
    """
    Returns a formatted string list of open pull request messages.
    """
    lines = []
    for repository in organization.repositories():
        if REPOSITORIES and repository.name.lower() not in REPOSITORIES:
            continue
        unchecked_pulls = fetch_repository_pulls(repository)
        lines += format_pull_requests(unchecked_pulls, organization.login,
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
    org = get_organization(ORGANIZATION)
    add_TEAMS_usernames_to_USERNAMES(org)
    lines = fetch_organization_pulls(org)
    if lines:
        text = INITIAL_MESSAGE + '\n'.join(lines)
        send_to_slack(text)

if __name__ == '__main__':
    cli()
