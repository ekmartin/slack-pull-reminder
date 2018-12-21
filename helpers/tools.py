import os
import sys
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

ignoreWords = os.environ.get('IGNORE_WORDS')
IGNORE_WORDS = [i.lower().strip() for i in ignoreWords.split(',')] if ignoreWords else []

ignoreLabels = os.environ.get('IGNORE_LABELS')
default_ignore_lables = ['wip']
IGNORE_LABELS = [i.lower().strip() for i in ignoreLabels.split(',')] if ignoreLabels else default_ignore_lables

usernames = os.environ.get('USERNAMES')
USERNAMES = [u.lower().strip() for u in usernames.split(',')] if usernames else []


"""
fetch and return open pulls of all users or specified users
""" 
def fetch_repository_pulls(repository):
    pulls = []
    for pull in repository.pull_requests():
        if pull.state == 'open' and (not USERNAMES or pull.user.login.lower() in USERNAMES):
            pulls.append(pull)

    return pulls

def fetch_pull_comments(pull):
    comments = []
    for comment in pull.review_comments():
        comments.append(comment)

    logger.debug('pull %#s, count of comments: %d', pull.number, len(comments))
    return comments

def get_pull_reviewers_days_ago(pulls, days = 1):
    authors = {}
    start_time = datetime.utcnow() + timedelta(days= -days)

    for pull in pulls:
        comments = fetch_pull_comments(pull)
        for comment in comments:
            comment_created_at = comment.created_at.replace(tzinfo=None)
            if comment_created_at < start_time:
                continue

            author = comment.user.login
            if author not in authors:
                authors[author] = []

            authors[author].append(comment)
    
    logger.info('authors: %s', authors)
    return authors

"""
exclude pull contains ignore keywords in title, or ignore labels
"""
def is_valid_pull(pull):
    if contains_ignore_word(pull.title):
        return False
    
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

def get_open_pulls_section(pulls):
    section_head = '\n ======================\n    Open PRs _*{0}*_\n======================\n\n'.format(len(pulls))
    lines = []

    for pull in pulls:
        creator = pull.user.login
        prTitle = pull.title.encode('utf-8')
        created_at = pull.created_at
        pull_age = (datetime.utcnow() - created_at.replace(tzinfo=None)).days
        requested_reviewers_string = ''
        if pull.requested_reviewers:
            logger.info(pull.requested_reviewers[0])
            requested_reviewers = map(lambda reviewer: '@' + reviewer.get('login'), pull.requested_reviewers)
            requested_reviewers_string = ', '.join(requested_reviewers)
        
        waiting_on = (' | waiting on ' + requested_reviewers_string + ', ') if requested_reviewers_string else ''


        line = '#{3} `{4} days` <{0}|{1}> {5} - by {2}'.format(pull.html_url, prTitle, creator, pull.number, pull_age, waiting_on)
        logger.debug('pull: %s', pull)

        lines.append(line)
    
    return section_head + '\n'.join(lines)

def get_review_contribution_section(pulls, days = 1):
    section_head = '\n ======================\n    CR Contributions _*{0}*_ days\n======================\n\n'.format(days)
    lines = []
    authors = get_pull_reviewers_days_ago(pulls, days)
    sorted_authors = sorted(authors, key=lambda author: len(authors[author]),  reverse=True)
    logger.info(authors)
    logger.info(sorted_authors)


    for index, author in enumerate(sorted_authors):
        logger.info('author: %s comments: %s', author, authors[author])
        comments = authors[author]
        if index == 0:
            line = ':trophy:: :fire:*{0}*:fire: added _{1}_ review comments\n'
        else:
            line = ':ninja:: *{0}* added _{1}_ review comments'

        lines.append(line.format(author, len(comments)))
    
    return section_head + '\n'.join(lines) + '\n============\n'

