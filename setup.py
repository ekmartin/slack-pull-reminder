from setuptools import setup

with open('README.rst', 'rb') as f:
    readme = f.read().decode('utf-8')

with open('requirements.txt', 'r') as fd:
    requirements = fd.read().strip().split('\n')

setup(
    name='slack-pull-reminder',
    version='0.1.0',
    url='http://github.com/ekmartin/slack-pull-reminder',
    author='Martin Ek',
    author_email='mail@ekmartin.com',
    description='Posts a Slack reminder with a list of open pull requests for an organization',
    long_description=readme,
    py_modules=['slack_pull_reminder'],
    license='MIT',
    install_requires=requirements,
    entry_points='''
        [console_scripts]
        slack_pull_reminder=slack_pull_reminder:cli
    '''
)
