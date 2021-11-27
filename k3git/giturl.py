#!/usr/bin/env python
# coding: utf-8

import os
import re

#  https://stackoverflow.com/questions/31801271/what-are-the-supported-git-url-formats
#  I found the list below. It is not complete since
#  https://<token>:x-oauth-basic@host.xz/path/to/repo.git is not there.
#
#  Secure Shell Transport Protocol
#  ssh://user@host.xz:port/path/to/repo.git/
#  ssh://user@host.xz/path/to/repo.git/
#  ssh://host.xz:port/path/to/repo.git/
#  ssh://host.xz/path/to/repo.git/
#  ssh://user@host.xz/path/to/repo.git/
#  ssh://host.xz/path/to/repo.git/
#  ssh://user@host.xz/~user/path/to/repo.git/
#  ssh://host.xz/~user/path/to/repo.git/
#  ssh://user@host.xz/~/path/to/repo.git
#  ssh://host.xz/~/path/to/repo.git
#  user@host.xz:/path/to/repo.git/
#  host.xz:/path/to/repo.git/
#  user@host.xz:~user/path/to/repo.git/
#  host.xz:~user/path/to/repo.git/
#  user@host.xz:path/to/repo.git
#  host.xz:path/to/repo.git
#  rsync://host.xz/path/to/repo.git/
#
#  Git Transport Protocol
#  git://host.xz/path/to/repo.git/
#  git://host.xz/~user/path/to/repo.git/
#
#  HTTP/S Transport Protocol
#  http://host.xz/path/to/repo.git/
#  https://host.xz/path/to/repo.git/

#  Secure Shell Transport Protocol

#  ssh://(?P<user>.*?)@(?P<host>.*?):(?P<port>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<user>.*?)@(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<host>.*?):(?P<port>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<user>.*?)@(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<user>.*?)@(?P<host>.*?)/~user/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<host>.*?)/~(?P<user>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<user>.*?)@(?P<host>.*?)/~/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<host>.*?)/~/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  (?P<user>.*?)@(?P<host>.*?):/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  (?P<host>.*?):/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  (?P<user>.*?)@(?P<host>.*?):~user/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  (?P<host>.*?):~(?P<user>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  (?P<user>.*?)@(?P<host>.*?):(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  (?P<host>.*?):(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  rsync://(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$

#  Git Transport Protocol

#  git://(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  git://(?P<host>.*?)/~(?P<user>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$

#  HTTP/S Transport Protocol

#  http://(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  https://(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$


rule_groups = [{
    "defaults": {
        "host": "github.com",
    },
    "env": {
        "committer": "GITHUB_USERNAME",
        "token": "GITHUB_TOKEN",
    },
    "provider": "github.com",
    "fmt": {
        "ssh": 'git@{host}:{user}/{repo}.git',
        "https": 'https://{host}/{user}/{repo}.git',
        "https_token": 'https://{committer}:{token}@{host}/{user}/{repo}.git',
    },
    "patterns": [
        # github.com/openacid/slim.git
        ('ssh', r'github.com/(?P<user>.+?)/(?P<repo>.+?)(\.git)?/?(?P<branch>@.+?)?$'),
        # git@github.com:openacid/slim.git
        ('ssh', r'git@github.com:(?P<user>.+?)/(?P<repo>.+?)(\.git)?/?(?P<branch>@.+?)?$'),
        # ssh://git@github.com/openacid/openacid.github.io
        ('ssh', r'ssh://git@github.com/(?P<user>.+?)/(?P<repo>.+?)(\.git)?/?(?P<branch>@.+?)?$'),
        # https://committer:token@github.com/openacid/openacid.github.io.git
        ('https',
         r'https://(?P<committer>.+?):(?P<token>.+?)@github.com/(?P<user>.+?)/(?P<repo>.+?)(\.git)?/?(?P<branch>@.+?)?$'),
        # http://github.com/openacid/openacid.github.io.git
        ('https', r'http://github.com/(?P<user>.+?)/(?P<repo>.+?)(\.git)?/?(?P<branch>@.+?)?$'),
        # https://github.com/openacid/openacid.github.io.git
        ('https', r'https://github.com/(?P<user>.+?)/(?P<repo>.+?)(\.git)?/?(?P<branch>@.+?)?$'),
    ],
}, {
    "defaults": {
    },
    "env": {
    },
    "provider": "*",
    "fmt": {
        "ssh": 'git@{host}:{user}/{repo}.git',
        "https": 'https://{host}/{user}/{repo}.git',
        "https_token": 'https://{committer}:{token}@{host}/{user}/{repo}.git',
    },
    "patterns": [
        ('https',
         r'https://(?P<committer>.+?):(?P<token>.+?)@(?P<host>.+?)/(?P<user>.+?)/(?P<repo>.+?)(\.git)?/?(?P<branch>@.+?)?$'),
        ('https', r'http://(?P<host>[^/]+?)/(?P<user>.+?)/(?P<repo>.+?)(\.git)?/?(?P<branch>@.+?)?$'),
        ('https', r'https://(?P<host>[^/]+?)/(?P<user>.+?)/(?P<repo>.+?)(\.git)?/?(?P<branch>@.+?)?$'),
        ('ssh', r'ssh://git@(?P<host>[^/]+?)/(?P<user>.+?)/(?P<repo>.+?)(\.git)?/?(?P<branch>@.+?)?$'),
        ('ssh', r'git@(?P<host>[^/]+?):(?P<user>.+?)/(?P<repo>.+?)(\.git)?/?(?P<branch>@.+?)?$'),
        ('ssh', r'(?P<host>[^/]+?)/(?P<user>.+?)/(?P<repo>.+?)(\.git)?/?(?P<branch>@.+?)?$'),
    ],

},
]


class GitUrl(object):
    """
    GitUrl parse and format git urls
    """

    def __init__(self, fields, rule_group, matching_pattern):
        """
        Create a GitUrl object.

        Args:

            fields(dict): fields of url components, such as 'user', 'repo',
                    'branch', 'token', 'committer'.

            rule_group(dict): one of the predefined rule group this git-url
                    matched and is also used to output plain text url.

            matching_pattern(str): the url pattern defined in rule_group that matches this url.
        """

        self.fields = fields
        self.rule_group = rule_group
        self.matching_pattern = matching_pattern

    def fmt(self, scheme=None):
        """
        format git url to scheme ssh or https

        Args:

           scheme(str): specifies the output url format:

                        - ``"ssh": 'git@{host}:{user}/{repo}.git'``,

                        - ``"https": 'https://{host}/{user}/{repo}.git'``,

                        - ``"https" with token present in fields: 'https://{committer}:{token}@{host}/{user}/{repo}.git'``,

                        If absent, format by fields['sheme']

        Returns:
            str: the formatted url
        """

        if scheme is None:
            scheme = self.fields['scheme']

        if scheme == 'https':
            if 'token' in self.fields:
                fmt = self.rule_group['fmt']['https_token']
            else:
                fmt = self.rule_group['fmt']['https']
        elif scheme == 'ssh':
            fmt = self.rule_group['fmt']['ssh']
        else:
            raise ValueError("invalid scheme: " + scheme)

        return fmt.format(**self.fields)

    @classmethod
    def parse(cls, url):
        """
        Parse plain text git url and return an instance of GitUrl.

        Args:

            url(str): git url in string in one form of:

                    - ``git@github.com:openacid/slim.git``
                    - ``ssh://git@github.com/openacid/openacid.github.io``
                    - ``https://committer:token@github.com/openacid/openacid.github.io.git``
                    - ``http://github.com/openacid/openacid.github.io.git``
                    - ``https://github.com/openacid/openacid.github.io.git``

        Returns:
            GitUrl
        """

        for g in rule_groups:
            for (scheme, p) in g['patterns']:
                match = re.match(p, url)
                if not match:
                    continue

                d = match.groupdict()
                d.update(g['defaults'])

                d['scheme'] = scheme

                #  extend vars from env
                for var_name, env_name in g['env'].items():
                    if var_name not in d:
                        v = os.environ.get(env_name)
                        if v is not None:
                            d[var_name] = v

                return cls(d, g, p)

        raise ValueError(
            'unknown url: {url};'.format(
                url=url,
            )
        )
