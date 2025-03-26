#
# Enthought product code
#
# (C) Copyright 2025 Enthought, Inc., Austin, TX
# All rights reserved.
#
# This file and its contents are confidential information and NOT open source.
# Distribution is prohibited.
#
import logging
from urllib.parse import ParseResult

import requests

DEFAULT_GITHUB_API_SERVER = "api.github.com"
DEFAULT_GITHUB_UPLOAD_SERVER = "uploads.github.com"
logger = logging.getLogger(__name__)


def get_release(repository, tag, token):
    """ Get the release tag info from github.

    Parameters
    ----------
    repository : str
        The name of the github repository of the release.
    tag : str
        The tag name of the release.
    token : str
        The OAuth token to use for authenticating with the git server.
    """
    url = ParseResult(
        'https', DEFAULT_GITHUB_API_SERVER,
        f'repos/enthought/{repository}/releases', '', '', '').geturl()
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28'}
    logger.info('Get release list')
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    for release in response.json():
        if release['tag_name'] == tag:
            return release
    else:
        raise ValueError(f'Could not find release with tag {tag}')
