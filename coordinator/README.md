# Pyroscope Operator

[![CharmHub Badge](https://charmhub.io/pyroscope-coordinator-k8s/badge.svg)](https://charmhub.io/pyroscope-coordinator-k8s)
[![Release](https://github.com/canonical/pyroscope-operators/actions/workflows/release.yaml/badge.svg)](https://github.com/canonical/pyroscope-operators/actions/workflows/release.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

This repository contains the source code for a Charmed Operator that drives [Pyroscope] on Kubernetes. It is destined to work together with [pyroscope-worker-k8s](https://charmhub.io/pyroscope-worker-k8s) to deploy and operate Grafana Pyroscope, a distributed profiling backend backed by Grafana. See [charmed Pyroscope HA](https://discourse.charmhub.io/t/18120) documentation for more details.

## Usage

Assuming you have access to a bootstrapped Juju controller on Kubernetes, you can:

```bash
$ juju deploy pyroscope-coordinator-k8s # --trust (use when cluster has RBAC enabled)
```

## OCI Images


## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines
on enhancements to this charm following best practice guidelines, and the
[contributing] doc for developer guidance.

[Pyroscope]: https://grafana.com/oss/pyroscope/
[contributing]: https://github.com/canonical/pyroscope-operators/blob/main/CONTRIBUTING.md
