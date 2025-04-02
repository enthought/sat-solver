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
import logging
import argparse
import shutil
from pathlib import Path
from urllib.parse import quote, urlparse

import requests

from .common import DEFAULT_GITHUB_API_SERVER, get_release

logger = logging.getLogger('download-assets')


def download_asset(asset, target, token, session):
    """ Download asset from a release.

    Parameters
    ----------
    asset : dict
        The get release response as a json dictionary.
    target : Path
        The folder to download the asset
    token : str
        The OAuth token to use for authenticating with the git server.
    """
    components = urlparse(asset["url"])
    assert components.scheme == 'https'
    assert components.netloc == DEFAULT_GITHUB_API_SERVER
    url = components.geturl()
    headers = {
        'Accept': 'application/octet-stream',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28'}
    with session.get(url, headers=headers, timeout=10, stream=True) as response:  # noqa
        response.raise_for_status()
        with (target / asset['name']).open('wb') as handle:
            shutil.copyfileobj(response.raw, handle)
        response.raise_for_status()
    logger.info(f'Downloaded {asset["name"]}')


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    logging.basicConfig(level=logging.INFO)
    pr = argparse.ArgumentParser(
        description='Upload artifacts to a release tag')
    pr.add_argument(
        '-r', '--repository', help='The github repository',
        default='sat-solver')
    pr.add_argument(
        '-t', '--token', help='The authentication token')
    pr.add_argument('tag', help='Release tag')
    pr.add_argument(
        '--folder', type=Path, default=Path('.'),
        help='The folder where to download the assets')
    args = pr.parse_args(argv)

    if args.token is None:
        args.token = os.environ.get(
            'GITHUB_OAUTH_TOKEN',
            os.environ.get('GITHUB_TOKEN', None))
    try:
        release = get_release(
            quote(args.repository), args.tag, args.token)
    except ValueError as exception:
        logger.error(exception)
        exit(-1)

    folder = Path(args.folder)
    assets = release['assets']
    if not folder.exists():
        os.makedirs(folder)
    with requests.Session() as session:
        for asset in assets:
            download_asset(asset, folder, args.token, session)


if __name__ == "__main__":
    main()
