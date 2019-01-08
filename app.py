from flask import Flask, request, make_response, render_template
from helpers.bot import SlackBot
from helpers.logger import logger, pp
from helpers.gh_events import gh_event_handler

app = Flask('pr-reminder')
slackBot = SlackBot()

@app.route('/')
def hello():
    return 'Hello World!'

@app.route('/slack/install', methods=['GET'])
def pre_install():
    """
    This route renders the installation page with 'Add to Slack' button.

    see https://api.slack.com/docs/oauth Step 1
    """
    client_id = slackBot.oauth["client_id"]
    scope = slackBot.oauth["scope"]
    # Our template is using the Jinja templating language to dynamically pass
    # our client id and scope
    return render_template("install.html", client_id=client_id, scope=scope)


@app.route("/slack/thanks", methods=["GET", "POST"])
def thanks():
    """
    This route is called by Slack after the user installs our app. It will
    exchange the temporary authorization code Slack sends for an OAuth token
    which we'll save on the bot object to use later.
    To let the user know what's happened it will also render a thank you page.
    see https://api.slack.com/docs/oauth Step 2
    """
    # Let's grab that temporary authorization code Slack's sent us from
    # the request's parameters.
    temp_auth_code = request.args.get('code')
    # The bot's auth method to handles exchanging the code for an OAuth token
    slackBot.auth(temp_auth_code)
    return render_template('thanks.html')

@app.route('/gh/events', methods=['POST'])
def gh_events():
    """
    This route is called by github for events notifying
    """
    gh_event_handler(request.json)

    return 'I am listening.'

@app.route('/gh/auth/callback', methods=['GET'])
def gh_auth_callback():
    """
    This route is used as `User authorization callback URL`
    """
    return 'Welcome to auth callback'


if __name__ == "__main__":
    app.run()
