# pyroscope-k8s-operator
This charmed operator is part of automating the operational procedures of running Grafana Pyroscope, an open-source profiling backend, in microservices mode.

This repository hosts two charms following the [coordinated-workers](https://discourse.charmhub.io/t/cos-lite-docs-managing-deployments-of-cos-lite-ha-addons/15213) pattern.
Together, they deploy and operate Grafana Pyroscope, an open-source profiling backend by Grafana Labs. See [charmed Pyroscope HA](https://discourse.charmhub.io/t/18120) documentation for more details.
 
The charm in `./coordinator` deploys and operates a configurator charm and an nginx instance responsible for routing traffic to the worker nodes.

The charm in `./worker` deploys and operates one or multiple roles of Pyroscope's distributed architecture.