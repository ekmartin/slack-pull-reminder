import os
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import requests
from github3 import login

POST_URL = 'https://slack.com/api/chat.postMessage'

ignore = os.environ.get('IGNORE_WORDS')
IGNORE_WORDS = [i.lower().strip() for i in ignore.split(',')] if ignore else []

repositories = os.environ.get('REPOSITORIES')
REPOSITORIES = [r.lower().strip() for r in repositories.split(',')] if repositories else []

usernames = os.environ.get('USERNAMES')
USERNAMES = [u.lower().strip() for u in usernames.split(',')] if usernames else []

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


def fetch_repository_pulls(repository):
    pulls = []
    for short_pull in repository.pull_requests():
        pull = repository.pull_request(short_pull.number)
        if pull.state == 'open' and (not USERNAMES or pull.user.login.lower() in USERNAMES):
            pulls.append(pull)
    return pulls


def is_valid_title(title):
    lowercase_title = title.lower()
    for ignored_word in IGNORE_WORDS:
        if ignored_word in lowercase_title:
            return False

    return True


def get_age(pull):
    td = datetime.now(timezone.utc) - pull.updated_at
    hours, _ = divmod(int(td.total_seconds()), 3600)
    return hours


def get_review_statuses(pull):
    dict = defaultdict(set)

    for review in pull.reviews():
        if review.state == 'APPROVED':
            state = ':white_check_mark:'
        elif review.state == 'CHANGES_REQUESTED':
            state = ':o:'
        else:
            continue
            
        dict[state].add('@{0}'.format(review.user.login))
    
    if dict:
        line = 'Reviews: ' + ' '.join(['{0} by {1}'.format(key, ', '.join(value)) for (key, value) in dict.items()])
    else:
        line = 'No reviews :warning:'
        
    return line


def is_mergeable(pull):
    line = ':-1:'
    if pull.mergeable:
        line = ':+1:'

    return line


def format_pull_requests(pull_requests, owner, repository):
    lines = []

    for pull in pull_requests:
        if is_valid_title(pull.title):
            creator = pull.user.login
            review_statuses = get_review_statuses(pull)
            mergeable = is_mergeable(pull)
            age = get_age(pull)
            line = '*[{0}/{1}]* <{2}|{3}> by @{4} • Updated {5}h ago • {6} • Mergeable: {7}'.format(
                owner, repository, pull.html_url, pull.title, creator, age, review_statuses, mergeable)
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
