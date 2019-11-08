import os
from collections import namedtuple

import requests
from github3 import login


class ConfigError(Exception):
    """generic error for the config class"""


class Config:
    def __init__(self):
        self._load_slack_configs()
        self._load_github_configs()

    def _load_slack_configs(self):
        # required fields
        try:
            self.SLACK_API_TOKEN = os.environ["SLACK_API_TOKEN"]
        except KeyError as error:
            ConfigError(f"Please set the environment variable {error}")

        self.SLACK_POST_URL = "https://slack.com/api/chat.postMessage"
        self.SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#general")
        self.SLACK_INITIAL_MESSAGE = """\
        Hi! There's a few open pull requests you should take a \
        look at:

        """

    def _load_github_configs(self):
        # required fields
        try:
            self.GITHUB_API_TOKEN = os.environ["GITHUB_API_TOKEN"]
            self.GITHUB_ORGANIZATION = os.environ["ORGANIZATION"]
        except KeyError as error:
            ConfigError(f"Please set the environment variable {error}")

        ignore = os.environ.get("IGNORE_WORDS")
        self.IGNORE_WORDS = (
            [i.lower().strip() for i in ignore.split(",")] if ignore else []
        )

        repositories = os.environ.get("REPOSITORIES")
        self.REPOSITORIES = (
            [r.lower().strip() for r in repositories.split(",")] if repositories else []
        )

        usernames = os.environ.get("USERNAMES")
        self.USERNAMES = (
            [u.lower().strip() for u in usernames.split(",")] if usernames else []
        )


PullRequest = namedtuple(
    "PullRequest", "repository_name pull_requests creator url title has_valid_title"
)


class GitHubDataProvider:
    def __init__(self, config):
        self._config = config

    def fetch_organization_pulls(self):
        """
        Returns a formatted string list of open pull request messages.
        """
        client = login(token=self._config.GITHUB_API_TOKEN)
        organization = client.organization(self._config.GITHUB_ORGANIZATION)

        open_prs = [
            self.fetch_repository_pulls(repository)
            for repository in organization.repositories()
            if self._is_required_fetch(repository)
        ]

        return [
            self.format_pull_request(pr, owner=self._config.GITHUB_ORGANIZATION)
            for pr in open_prs
            if pr.has_valid_title
        ]

    def _is_required_fetch(self, repository):
        return repository.name.lower() in self._config.REPOSITORIES

    def fetch_repository_pulls(self, repository):
        def return_obj(open_pull_requests):
            return [
                PullRequest(
                    repository_name=repository.name,
                    pull_requests=pull,
                    creator=pull.user.login,
                    url=pull.html_url,
                    title=pull.title,
                    has_valid_title=self._is_valid_title(pull.title),
                )
                for pull in open_pull_requests
            ]

        open_pull_requests = [
            pull for pull in repository.pull_requests() if pull.state == "open"
        ]

        if not self._config.USERNAMES:
            return return_obj(open_pull_requests)

        return return_obj(
            [
                pull
                for pull in open_pull_requests
                if pull.user.login.lower() in self._config.USERNAMES
            ]
        )

    def format_pull_request(self, pull, owner=""):
        return f"*[{owner}/{pull.repository_name}]* <{pull.url}|{pull.title} - by {pull.creator}>"

    def _is_valid_title(self, title):
        lowercase_title = title.lower()
        for ignored_word in self._config.IGNORE_WORDS:
            if ignored_word in lowercase_title:
                return False

        return True


class Slack:
    def __init__(self, config):
        self._config = config

    def send(self, text):
        payload = {
            "token": self._config.SLACK_API_TOKEN,
            "channel": self._config.SLACK_CHANNEL,
            "username": "Pull Request Reminder",
            "icon_emoji": ":bell:",
            "text": text,
        }

        response = requests.post(self._config.SLACK_POST_URL, data=payload)
        answer = response.json()
        if not answer["ok"]:
            raise Exception(answer["error"])


def cli():
    config = Config()
    github = GitHubDataProvider(config)
    slack = Slack(config)

    lines = github.fetch_organization_pulls()
    if lines:
        text = config.SLACK_INITIAL_MESSAGE + "\n".join(lines)
        slack.send(text)


if __name__ == "__main__":
    cli()
