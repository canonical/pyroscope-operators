# Terraform module for pyroscope solution

This is a Terraform module facilitating the deployment of pyroscope solution, using the [Terraform juju provider](https://github.com/juju/terraform-provider-juju/). For more information, refer to the provider [documentation](https://registry.terraform.io/providers/juju/juju/latest/docs).

The solution consists of the following Terraform modules:
- [pyroscope-coordinator-k8s](https://github.com/canonical/pyroscope-k8s-operator/tree/main/coordinator): ingress, cluster coordination, single integration facade.
- [pyroscope-worker-k8s](https://github.com/canonical/pyroscope-k8s-operator/tree/main/worker): run one or more pyroscope application components.
- [s3-integrator](https://github.com/canonical/s3-integrator): facade for S3 storage configurations.

This Terraform module deploys pyroscope in its [microservices mode](https://grafana.com/docs/pyroscope/latest/reference-pyroscope-architecture/deployment-modes/#microservices-mode), which runs each one of the required roles in distinct processes. [See](https://discourse.charmhub.io/t/topic/15213) to understand more about pyroscope roles.


> [!NOTE]
> `s3-integrator` itself doesn't act as an S3 object storage system. For the solution to be functional, `s3-integrator` needs to point to an S3-like storage. See [this guide](https://discourse.charmhub.io/t/cos-lite-docs-set-up-minio/15211) to learn how to connect to an S3-like storage for traces.

## Requirements
This module requires a `juju` model to be available. Refer to the [usage section](#usage) below for more details.

## API

### Inputs
The module offers the following configurable inputs:

| Name | Type | Description | Default |
| - | - | - | - |
| `channel`| string | Channel that the charms are deployed from |  |
| `compactor_units`| number | Number of pyroscope worker units with compactor role | 1 |
| `distributor_units`| number | Number of pyroscope worker units with distributor role | 1 |
| `ingester_units`| number | Number of pyroscope worker units with ingester role | 1 |
| `query_scheduler_units`| number | Number of pyroscope worker units with query-scheduler role | 1 |
| `model`| string | Name of the model that the charm is deployed on |  |
| `querier_units`| number | Number of pyroscope worker units with querier role | 1 |
| `query_frontend_units`| number | Number of pyroscope worker units with query-frontend role | 1 |
| `store_gateway_units`| number | Number of pyroscope worker units with store-gateway role | 1 |
| `tenant_settings_units`| number | Number of pyroscope worker units with tenant-settings role | 1 |
| `ad_hoc_profiles_units`| number | Number of pyroscope worker units with ad-hoc-profiles role | 1 |
| `coordinator_units`| number | Number of pyroscope coordinator units | 1 |
| `s3_integrator_name` | string | Name of the s3-integrator app | 1 |
| `s3_bucket` | string | Name of the bucket in which pyroscope stores traces | 1 |
| `s3_access_key` | string | Access key credential to connect to the S3 provider | 1 |
| `s3_secret_key` | string | Secret key credential to connect to the S3 provider | 1 |
| `s3_endpoint` | string | Endpoint of the S3 provider | 1 |


### Outputs
Upon application, the module exports the following outputs:

| Name | Type | Description |
| - | - | - |
| `app_names`| map(string) | Names of the deployed applications |
| `endpoints`| map(string) | Map of all `provides` and `requires` endpoints |

## Usage


### Basic usage

Users should ensure that Terraform is aware of the `juju_model` dependency of the charm module.

To deploy this module with its needed dependency, you can run `terraform apply -var="model=<MODEL_NAME>" -auto-approve`. This would deploy all pyroscope components in the same model.

### Microservice deployment

By default, this Terraform module will deploy each pyroscope worker with `1` unit. To configure the module to run `x` units of any worker role, you can run `terraform apply -var="model=<MODEL_NAME>" -var="<ROLE>_units=<x>" -auto-approve`.
See [pyroscope worker roles](https://discourse.charmhub.io/t/pyroscope-worker-roles/15484) for the recommended scale for each role.
