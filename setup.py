from setuptools import setup

with open('README.rst', 'rb') as f:
    readme = f.read().decode('utf-8')

setup(
    name='pr-reminder',
    version='0.1.5',
    url='http://github.com/ekmartin/slack-pull-reminder',
    author='Martin Ek',
    author_email='mail@ekmartin.com',
    description='Posts a Slack reminder with a list of open pull requests for an organization',
    long_description=readme,
    py_modules=['pr_reminder'],
    license='MIT',
    install_requires=[
        'requests==2.20.1',
        'github3.py==1.0.0a4'
    ],
    entry_points='''
        [console_scripts]
        pr-reminder=slack_pull_reminder:cli
    '''
)
