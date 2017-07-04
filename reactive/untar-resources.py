# Core packages
import os
import pwd
import shutil
import subprocess
import tarfile
from hashlib import md5

# Third-party packages
from charmhelpers.core.hookenv import (
    log,
    resource_get,
    status_set
)
from charms.reactive import hook, remove_state, set_state
import yaml


# Read layer config, with defaults
if not os.path.exists('untar-resources.yaml'):
    raise Exception('untar-resources.yaml not found')

with open('untar-resources.yaml') as layer_config_yaml:
    layer_config = yaml.safe_load(layer_config_yaml.read())


def _get_user(username):
    """
    Get or create user
    """

    try:
        user = pwd.getpwnam(username)
    except KeyError:
        subprocess.check_call(['useradd', username])
        user = pwd.getpwnam(username)

    return user


def _chown_recursive(path, username, groupname):
    user = _get_user(username)

    for root, dirs, files in os.walk(path):
        for momo in files + dirs:
            os.chown(os.path.join(root, momo), user.pw_uid, user.pw_gid)

    os.chown(path, user.pw_uid, user.pw_gid)


def _log(message):
    log('[untar-resources] {}'.format(message))


@hook('install', 'upgrade-charm')
def update_resources():
    resources_config = layer_config['resources']

    for resource_name, resource_config in resources_config.items():
        destination_path = resource_config['destination_path']
        username = resource_config['username']

        resource_path = resource_get(resource_name)

        if not resource_path:
            status_set(
                'blocked',
                '[untar-resources] Resource "{}" missing'.format(resource_name)
            )
            set_state('resources.{}.missing'.format(resource_name))
            return
        else:
            remove_state('resources.{}.missing'.format(resource_name))

        status_set(
            'maintenance',
            '[untar-resources] Extracting resource "{}"'.format(resource_name)
        )

        target_path = destination_path.rstrip('/')
        next_path = destination_path + '.next'
        hash_path = destination_path + '.hash'
        previous_path = destination_path + '.previous'

        _log('Reading hash of {}'.format(resource_path))
        resource_hash = md5()
        with open(resource_path, "rb") as resource:
            # Load file half a MP at a time
            for chunk in iter(lambda: resource.read(524288), b""):
                resource_hash.update(chunk)
        resource_hex = resource_hash.hexdigest()

        existing_hex = None
        if os.path.exists(hash_path):
            with open(hash_path) as hash_file:
                existing_hex = hash_file.read()

        if resource_hex == existing_hex:
            _log('{} hash {} already extracted'.format(
                resource_name, resource_hex
            ))

            status_set(
                'active',
                '[untar-resources] Resource "{}" available at {}'.format(
                    resource_name,
                    target_path
                )
            )
            set_state('resources.{}.available'.format(resource_name))

            return
        else:
            _log('Extracting {} with hash: {}'.format(
                resource_name, resource_hex
            ))

        _log('Creating {}'.format(next_path))
        os.makedirs(next_path, exist_ok=True)

        _log('Extracting {} into {}'.format(resource_path, next_path))
        tar = tarfile.open(resource_path)
        tar.extractall(next_path)
        tar.close()

        _log('Setting ownership to {}'.format(username))
        _chown_recursive(next_path, username, username)

        # Remove previous version
        if os.path.isdir(previous_path):
            _log('Removing previous version from {}'.format(previous_path))
            shutil.rmtree(previous_path)

        _log((
                'Installing new version: Moving {next_path} -> {target_path} '
                'and {target_path} -> {previous_path}'
        ).format(**locals()))

        move_command = ["mv", ]

        if os.listdir(target_path):
            # If target directory has contents, backup
            subprocess.check_call(
                [
                    "mv",
                    "--no-target-directory", "--backup", "--suffix=.previous",
                    next_path,
                    target_path
                ]
            )
        else:
            # Otherwise, simply replace
            subprocess.check_call(
                ["mv", "--no-target-directory", next_path, target_path]
            )

        _log('Setting {} to {}'.format(hash_path, resource_hex))
        with open(hash_path, 'w') as hash_file:
            hash_file.write(resource_hex)

        status_set(
            'active',
            '[untar-resources] Resource "{}" available at {}'.format(
                resource_name,
                target_path
            )
        )
        set_state('resources.{}.available'.format(resource_name))
