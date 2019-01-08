from message import send_to_slack_user
from logger import logger, pp

def gh_event_handler(event):
    event_action = event['action']
    if event_action == 'review_requested' or event_action == 'review_request_removed':
        review_requested_handler(event)
    else:
        logger.info('I am else of gh_event_handler')

"""
review_requested and review_request_removed events handle
"""
def review_requested_handler(event):
    event_action = event['action']
    pull_request = event['pull_request']

    # requested or removed reviewer
    updated_reviewer = event['requested_reviewer']['login']
    sender = event['sender']['login']

    # pull request meta data
    pull_number = pull_request['number']
    pull_url = pull_request['html_url']
    pull_title = pull_request['title']

    pull_str = '[#{0}: {1}]({2})'.format(pull_number, pull_title, pull_url)

    if event_action == 'review_requested':
        reminder_message = '{0} requested you to CR {1}'.format(sender, pull_str)
    elif event_action == 'review_request_removed':
        reminder_message = 'You are removed as a reviewer for PR {0}'.format(pull_str)

    # send_to_slack_user(reminder_message, '@' + updated_reviewer)
    logger.info('remind message %s', reminder_message)

