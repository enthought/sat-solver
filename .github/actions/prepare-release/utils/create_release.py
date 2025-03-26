#
# Enthought product code
#
# (C) Copyright 2025 Enthought, Inc., Austin, TX
# All rights reserved.
#
# This file and its contents are confidential information and NOT open source.
# Distribution is prohibited.
#
import os
import sys
import json
import logging
import argparse
from urllib.parse import quote, urlparse, ParseResult

import requests

from .common import DEFAULT_GITHUB_API_SERVER, get_release

logger = logging.getLogger('create-release')


def create_release(repository, tag, token):
    """ download asset and halculate sha256 hash

    Parameters
    ----------
    repository : str
        The name of the github repository of the release.
    tag : str
        The tag to create a release on.
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
    data = {
        'tag_name': tag,
        'name': f'{tag} Python runtime',
        'body': '',
        'draft': True,
        'prerelease': False,
        'generate_release_notes': True}
    logger.info(f'Create release for {tag}')
    response = requests.post(
        url, headers=headers, data=json.dumps(data), timeout=30)
    response.raise_for_status()


def delete_release(release, token):
    """ List assets in the release tag

    Parameters
    ----------
    release : dict
        The get release response as a json dictionary.
    token : str
        The OAuth token to use for authenticating with the git server.
    """
    components = urlparse(release["url"])
    assert components.scheme == 'https'
    assert components.netloc == DEFAULT_GITHUB_API_SERVER
    url = components.geturl()
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28'}
    response = requests.delete(url, headers=headers, timeout=30)
    response.raise_for_status()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    logging.basicConfig(level=logging.INFO)
    pr = argparse.ArgumentParser(
        description='Create a github release on tag')
    pr.add_argument(
        '-r', '--repository', help='The github repository',
        default='sat-solver')
    pr.add_argument(
        '-t', '--token', help='The authentication token')
    pr.add_argument(
        '--force', action='store_true',
        help='Always replace release if it exists')
    pr.add_argument(
        '--ignore', action='store_true',
        help='Do not fail if release exists')
    pr.add_argument('tag', help='Release tag')
    args = pr.parse_args(argv)

    if args.token is None:
        args.token = os.environ.get(
            'GITHUB_OAUTH_TOKEN',
            os.environ.get('GITHUB_TOKEN', None))
    repository = quote(args.repository)
    try:
        release = get_release(
            repository, args.tag, args.token)
    except ValueError:
        create_release(repository, args.tag, args.token)
        exit(0)
    if args.force:
        logger.warning(f'Found release for {args.tag}')
        delete_release(release, args.token)
        create_release(repository, args.tag, args.token)
    elif args.ignore:
        logger.warning(f'Found release for {args.tag}')
        exit(0)
    else:
        logger.error(f'Found release for {args.tag}')
        exit(-1)


if __name__ == "__main__":
    main()
