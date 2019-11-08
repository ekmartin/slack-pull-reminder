import os
import logging
import itertools
from pprint import pformat, pprint
from collections import namedtuple

import requests
from github3 import login

logging.basicConfig()
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """generic error for the config class"""


class Config:
    def __init__(self):
        # self._load_slack_configs()
        self._load_github_configs()
        self.LOGLEVEL = os.environ.get("LOGLEVEL", logging.INFO)

    def _load_slack_configs(self):
        # required fields
        try:
            self.SLACK_API_TOKEN = os.environ["SLACK_API_TOKEN"]
        except KeyError as error:
            raise ConfigError(f"please set the environment variable {error}")

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
            self.GITHUB_ORGANIZATION = os.environ["GITHUB_ORGANIZATION"]
        except KeyError as error:
            raise ConfigError(f"please set the environment variable {error}")

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
    "PullRequest", "repository_name creator url title has_valid_title pull_requests"
)


class GitHubDataProvider:
    def __init__(self, config):
        self._config = config

    def fetch_organization_pulls(self):
        """
        Returns a formatted string list of open pull request messages.
        """
        logger.info("authenticating to github")

        client = login(token=self._config.GITHUB_API_TOKEN)
        organization = client.organization(self._config.GITHUB_ORGANIZATION)

        logger.info(
            "fetching repositories pull requests from %s",
            self._config.GITHUB_ORGANIZATION,
        )

        organization_repositories = list(organization.repositories())
        logger.info(
            "organization repositories:\n%s",
            self._get_repo_names(organization_repositories),
        )

        open_prs_nested = [
            self._fetch_repository_pulls(repository)
            for repository in organization_repositories
            if self._is_required_fetch(repository)
        ]
        flatten = lambda l: [item for sublist in l for item in sublist]
        open_prs = flatten(open_prs_nested)
        logger.info(
            "required fetches PRs:\n%s", pformat(self._get_prs_titles(open_prs))
        )

        return [
            self._format_pull_request(pr, owner=self._config.GITHUB_ORGANIZATION)
            for pr in open_prs
            if pr.has_valid_title
        ]

    def _is_required_fetch(self, repository):
        return repository.name.lower() in self._config.REPOSITORIES

    def _fetch_repository_pulls(self, repository):
        def return_obj(open_pull_requests: list):
            return [
                PullRequest(
                    repository_name=repository.name,
                    creator=pull.user.login,
                    url=pull.html_url,
                    title=pull.title,
                    has_valid_title=self._is_valid_title(pull.title),
                    pull_requests=None,  # pull,
                )
                for pull in open_pull_requests
            ]

        open_pull_requests = [
            pull for pull in repository.pull_requests() if pull.state == "open"
        ]

        logger.info(
            "%s open pull requests:\n%s",
            repository.name,
            pformat(self._get_prs_titles(open_pull_requests)),
        )

        if not self._config.USERNAMES:
            logger.warning("username not specified, using all pull requests")
            return return_obj(open_pull_requests)

        return return_obj(
            [
                pull
                for pull in open_pull_requests
                if pull.user.login.lower() in self._config.USERNAMES
            ]
        )

    def _format_pull_request(self, pull, owner=""):
        return f"*[{owner}/{pull.repository_name}]* <{pull.url}|{pull.title} - by {pull.creator}>"

    def _is_valid_title(self, title):
        lowercase_title = title.lower()
        for ignored_word in self._config.IGNORE_WORDS:
            if ignored_word in lowercase_title:
                return False

        return True

    def _get_repo_names(self, repos):
        return [repo.name for repo in repos]

    def _get_prs_titles(self, pull_requests):
        return [pull.title for pull in pull_requests]


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
    logger.setLevel(config.LOGLEVEL)
    github = GitHubDataProvider(config)
    slack = Slack(config)

    lines = github.fetch_organization_pulls()
    logger.info("organization pulls: %s", pformat(lines))
    # if lines:
    #     text = config.SLACK_INITIAL_MESSAGE + "\n".join(lines)
    #     slack.send(text)


if __name__ == "__main__":
    try:
        cli()
    except ConfigError as err:
        logger.error(err)
        exit(1)

