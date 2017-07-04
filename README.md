# Charm layer: untar-resources

A [charm layer](https://jujucharms.com/docs/2.1/developer-layers) for extracting [gzipped tarballs](http://computing.help.inf.ed.ac.uk/FAQ/whats-tarball-or-how-do-i-unpack-or-create-tgz-or-targz-file) attached to the charm as [Juju resources](https://insights.ubuntu.com/2016/02/15/introducing-juju-resources/).

## Usage

Include this layer in your charm by adding it to `layer.yaml` in your charm root:

``` yaml
includes: ['layer:untar-resources', ...]
```

### Configuration

First, make sure your charm is specifying each of the resources you wish to manage in its `metadata.yaml`:

``` yaml
resources:
    {resource_name}:
        type: file
        filename: {filename}.tar.gz
        description: "{description}"
```

Now create a `untar-resources.yaml` file in your charm root to configure each `.tar.gz` resource you wish to extract:

``` yaml
resources:
    {resource_name}:
        username: {username}
        destination_path: {destination_path}
    {resource_name_2}:
        ...
```

## Behaviour

When the charm is built and deployed, resources can be attached using Juju:

``` bash
juju attach {service_name} {resource_name}={path_to_file}.tar.gz
```

The untar-resources layer will:

- detect the new resource
- extract it into the configured `{destination_path}`
- change ownership on the extracted files to `{username}`

If a newer resource is attached the contents of `{destination_path}` will be replaces, and a backup of the previous resource will be kept in `{destination_path}.previous`. Older versions of resources will be descarded.

## Example

For an example implementation, see the Webteam's [wsgi-app](https://github.com/canonical-websites/wsgi-app) charm.
