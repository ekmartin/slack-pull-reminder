from flask import Flask, request, make_response, render_template
from helpers.bot import SlackBot

app = Flask('pr-reminder')
slackBot = SlackBot()

@app.route('/')
def hello():
    return 'Hello World!'

@app.route('/install', methods=['GET'])
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


@app.route("/thanks", methods=["GET", "POST"])
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

if __name__ == "__main__":
    app.run()
