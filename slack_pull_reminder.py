import os
import sys
from collections import namedtuple

import requests
from github3 import login
from github3.repos import status

CombinedBuildStatus = namedtuple('CombinedBuildStatus', ('success', 'pending', 'failure'))

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
    CombinedBuildStatus.success: SUCCESS_EMOJI,
    CombinedBuildStatus.pending: PENDING_EMOJI,
    CombinedBuildStatus.failure: FAILURE_EMOJI,
    None: ' '  # for when there is no status for one PR but you still want the rest of the text to line up
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


def fetch_combined_build_status(pull_request):
    """
    Can't use the github api pull request combined statuses endpoint as for some reason it combines review statuses
    and build statuses and we only want build statuses
    :param pull_request: github3.py PullRequest obj
    :return: a CombinedBuildStatus enum value or None if no statuses
    """
    build_statuses = fetch_pull_request_build_statuses(pull_request)

    # { status.context: most recently updated Status with that context}
    most_recent_status_by_context = {}

    for build_status in build_statuses:
        if build_status.updated_at is None:
            # gihub3.py seems to imply this can be None, so ignore those statuses
            continue

        if build_status.context not in most_recent_status_by_context:
            most_recent_status_by_context[build_status.context] = build_status
        elif build_status.updated_at > most_recent_status_by_context[build_status.context].updated_at:
            most_recent_status_by_context[build_status.context] = build_status

    most_recent_statuses = most_recent_status_by_context.values()

    if len(most_recent_statuses) == 0:
        # no statuses, return None
        return None

    any_pending = False
    for status in most_recent_statuses:
        if status.state == CombinedBuildStatus.failure:
            # if any failed, return overall failure
            return CombinedBuildStatus.failure
        if status.state == CombinedBuildStatus.pending:
            # can't return here in case there's a failed one after it
            any_pending = True
    return CombinedBuildStatus.pending if any_pending else CombinedBuildStatus.success


def fetch_pull_request_build_statuses(pull_request):
    """
    # TODO Remove after the PR adding this is merged into github3.py
    # PR: https://github.com/sigmavirus24/github3.py/pull/896
    Return iterator of all Statuses associated with head of this pull request.

     :param pull_request: PullRequest object
    :returns:
        generator of statuses for this pull request
    :rtype:
        :class:`~github3.repos.Status`
    """
    if pull_request.repository is None:
        return []
    url = pull_request._build_url(
        'statuses', pull_request.head.sha, base_url=pull_request.repository._api
    )
    return pull_request._iter(-1, url, status.Status)


def format_pull_requests(pull_requests, owner, repository):
    lines = []

    for pull in pull_requests:
        if is_valid_title(pull.title):
            creator = pull.user.login
            combined_status = fetch_combined_build_status(pull)
            if SHOW_BUILD_STATUS and combined_status:
                build_status = state_to_emoji.get(combined_status)
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
