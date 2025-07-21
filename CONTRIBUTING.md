# Contributing

## Overview

This documents explains the processes and practices recommended for contributing enhancements to
this operator.

- Generally, before developing enhancements to this charm, you should consider [opening an issue
  ](https://github.com/canonical/pyroscope-operators/issues) explaining your use case.
- If you would like to chat with us about your use-cases or proposed implementation, you can reach
  us at the [Canonical Observability Matrix public channel](https://matrix.to/#/#cos:ubuntu.com)
  or [Discourse](https://discourse.charmhub.io/).
- Familiarising yourself with the [Charmed Operator Framework](https://juju.is/docs/sdk) library
  will help you a lot when working on new features or bug fixes.
- All enhancements require review before being merged. Code review typically examines
  - code quality
  - test coverage
  - user experience for Juju administrators this charm.
- Please help us out in ensuring easy to review branches by rebasing your pull request branch onto
  the `main` branch. This also avoids merge commits and creates a linear Git commit history.

## Developing

You can use the environments created by `tox` for development:

```shell
tox --notest -e unit
source .tox/unit/bin/activate
```

### Container images

We are using the following images built by [oci-factory](https://github.com/canonical/oci-factory):
- `ubuntu/pyroscope`
  - [source](https://github.com/canonical/pyroscope-rock)
  - [dockerhub](https://hub.docker.com/r/ubuntu/pyroscope)
- `ubuntu/nginx`
  - [source](https://github.com/canonical/nginx-rock)
  - [dockerhub](https://hub.docker.com/r/ubuntu/nginx)
- `nginx/nginx-prometheus-exporter`
  - (upstream image) (WIP: https://github.com/canonical/nginx-prometheus-exporter-rock)
  - [dockerhub](https://hub.docker.com/r/nginx/nginx-prometheus-exporter)

### Testing

```shell
tox -e fmt           # update your code according to formatting rules
tox -e lint          # lint the codebase
tox -e unit          # run the unit testing suite
tox -e integration   # run the integration testing suite
tox                  # runs 'lint' and 'unit' environments
```

## Build charm

Build the charm in this git repository using:

```shell
cd ./worker; charmcraft pack
cd ./coordinator; charmcraft pack
```

This will create:
- `coordinator/pyroscope-coordinator-k8s_ubuntu@24.04-amd64.charm`
- `worker/pyroscope-worker-k8s_ubuntu@24.04-amd64.charm`

### Deploy

```bash
# Create a model
juju add-model dev
# Enable DEBUG logging
juju model-config logging-config="<root>=INFO;unit=DEBUG"
# Deploy the charm
juju deploy ./coordinator/pyroscope-coordinator-k8s_ubuntu@24.04-amd64.charm \
    --resource nginx-image=ubuntu/nginx:1.24-24.04_beta \
    --resource nginx-prometheus-exporter-image=nginx/nginx-prometheus-exporter:1.1.0 \
    --trust pyroscope
juju deploy ./worker/pyroscope-worker-k8s_ubuntu@24.04-amd64.charm \
    --resource pyroscope-image=ubuntu/pyroscope:1.14-24.04_edge \
    --trust pyroscope-worker
juju integrate pyroscope pyroscope-worker
```

You'll also need an s3-compatible backend such as Ceph or Minio and an [s3-integrator charm](https://charmhub.io/s3-integrator). See [this doc](https://discourse.charmhub.io/t/cos-lite-docs-set-up-minio-for-s3-testing/15211) for more details.