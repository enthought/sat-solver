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
import hashlib
import logging
import argparse
from pathlib import Path
from urllib.parse import quote, urlparse

import requests

from .common import (
    DEFAULT_GITHUB_API_SERVER,
    DEFAULT_GITHUB_UPLOAD_SERVER, get_release)

logger = logging.getLogger('upload-assets')


def asset_hash(asset, token):
    """ Download asset and halculate sha256 hash

    Parameters
    ----------
    asset : dict
        The get release response as a json dictionary.
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
    logger.info(f'Calculating asset hash for {asset["name"]}')
    response = requests.get(url, headers=headers, timeout=5)
    response.raise_for_status()
    return hashlib.sha256(response.content).hexdigest()


def delete_asset(asset, token):
    """ List assets in the release tag

    Parameters
    ----------
    release : dict
        The get release response as a json dictionary.
    token : str
        The OAuth token to use for authenticating with the git server.
    """
    components = urlparse(asset["url"])
    assert components.scheme == 'https'
    assert components.netloc == DEFAULT_GITHUB_API_SERVER
    url = components.geturl()
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28'}
    response = requests.delete(url, headers=headers, timeout=30)
    logger.info(f'Asset {asset["name"]} deleted')
    response.raise_for_status()


def upload_asset(release, filename, token):
    """ Upload an asset to the release tag.

    Parameters
    ----------
    release : dict
        The get release response as a json dictionary.
    binary : Path
        The path of the binary file to upload.
    token : str
        The OAuth token to use for authenticating with the git server.
    """
    # The urllib.parse does not properly parse the upload_url
    components = urlparse(release["assets_url"])
    assert components.scheme == 'https'
    components = components._replace(netloc=DEFAULT_GITHUB_UPLOAD_SERVER)
    url = components.geturl()
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/octet-stream'}
    params = {'name': f'{filename.name}'}
    with filename.open('rb') as handle:
        respone = requests.post(
            url, params=params, data=handle,
            headers=headers, timeout=30)
    respone.raise_for_status()
    logger.info(f'Asset {filename.name} uploaded')


def check_hash(path, checksum):
    """ Check the sha256 checksum of a file.

    """
    logger.info(f'Checking sha256 for {path}')
    sha256 = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            sha256.update(chunk)

    hexdigest = sha256.hexdigest()
    if hexdigest != checksum:
        raise ValueError(f'File sha256 ({hexdigest}) is not {checksum}')


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
    pr.add_argument(
        '--force', action='store_true',
        help='Always replace asset if it exists')
    pr.add_argument(
        '--replace', action='store_true',
        help='Replace assets if it is different')
    pr.add_argument('tag', help='Release tag')
    pr.add_argument('folder', help='The folder with the assets to upload')
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

    assets = release['assets']
    for archive in Path(args.folder).glob('*'):
        logger.info(f'Checking {archive.name}')

        try:
            asset = next(
                asset for asset in assets
                if archive.name == asset['name'])
        except StopIteration:
            upload_asset(release, archive, args.token)
            continue
        else:
            logger.warning(f'Found asset {archive.name}')

        if args.force:
            delete_asset(asset, args.token)
            upload_asset(release, archive, args.token)
            continue

        try:
            check_hash(archive, asset_hash(asset, args.token))
        except ValueError:
            msg = f'Found asset {archive.name} but hashes do not match'
            if args.replace:
                logger.info(msg)
                delete_asset(asset, args.token)
                upload_asset(release, archive, args.token)
            else:
                logger.error(msg)
                exit(-1)
        else:
            logger.info('sha256 checksum match, asset already uploaded')


if __name__ == "__main__":
    main()
