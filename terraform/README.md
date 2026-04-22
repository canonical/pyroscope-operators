# Terraform module for pyroscope solution

This is a Terraform module facilitating the deployment of pyroscope solution, using the [Terraform juju provider](https://github.com/juju/terraform-provider-juju/). For more information, refer to the provider [documentation](https://registry.terraform.io/providers/juju/juju/latest/docs).

The solution consists of the following Terraform modules:
- [pyroscope-coordinator-k8s](https://github.com/canonical/pyroscope-operators/tree/main/coordinator): ingress, cluster coordination, single integration facade.
- [pyroscope-worker-k8s](https://github.com/canonical/pyroscope-operators/tree/main/worker): run one or more pyroscope application components.
- [s3-integrator](https://github.com/canonical/s3-integrator): facade for S3 storage configurations.

This Terraform module deploys pyroscope in its [microservices mode](https://grafana.com/docs/pyroscope/latest/reference-pyroscope-architecture/deployment-modes/#microservices-mode), which runs each one of the required roles in distinct processes. [See](https://discourse.charmhub.io/t/topic/15213) to understand more about pyroscope roles.


> [!NOTE]
> `s3-integrator` itself doesn't act as an S3 object storage system. For the solution to be functional, `s3-integrator` needs to point to an S3-like storage. See [this guide](https://discourse.charmhub.io/t/cos-lite-docs-set-up-minio/15211) to learn how to connect to an S3-like storage for traces.

## Requirements
This module requires a `juju` model to be available. Refer to the [usage section](#usage) below for more details.

## API

### Inputs
The module offers the following configurable inputs:

| Name                                        | Type        | Description                                                                                              | Default |
|---------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------|---------|
| `model`                                     | string      | Name of the model that the charm is deployed on                                                          |         |
| `channel`                                   | string      | Channel that the charms are deployed from                                                                |         |
| `coordinator_units`                         | number      | Number of pyroscope coordinator units                                                                    | 1       |
| `coordinator_strorage_directives`           | map(string) | Map of storage used by the coordinator application, which defaults to 1 GB, allocated by Juju            | {}      |
| `ad_hoc_profiles_units`                     | number      | Number of pyroscope worker units with ad-hoc-profiles role                                               | 1       |
| `ad_hoc_profiles_worker_storage_directives` | map(string) | Map of storage used by the ad-hoc-profiles worker application, which defaults to 1 GB, allocated by Juju | {}      |
| `compactor_units`                           | number      | Number of pyroscope worker units with compactor role                                                     | 1       |
| `compactor_worker_storage_directives`       | map(string) | Map of storage used by the compactor worker application, which defaults to 1 GB, allocated by Juju       | {}      |
| `distributor_units`                         | number      | Number of pyroscope worker units with distributor role                                                   | 1       |
| `distributor_worker_storage_directives`     | map(string) | Map of storage used by the distributor worker application, which defaults to 1 GB, allocated by Juju     | {}      |
| `ingester_units`                            | number      | Number of pyroscope worker units with ingester role                                                      | 1       |
| `ingester_worker_storage_directives`        | map(string) | Map of storage used by the ingester worker application, which defaults to 1 GB, allocated by Juju        | {}      |
| `querier_units`                             | number      | Number of pyroscope worker units with querier role                                                       | 1       |
| `querier_worker_storage_directives`         | map(string) | Map of storage used by the querier worker application, which defaults to 1 GB, allocated by Juju         | {}      |
| `query_frontend_units`                      | number      | Number of pyroscope worker units with query-frontend role                                                | 1       |
| `query_frontend_worker_storage_directives`  | map(string) | Map of storage used by the query-frontend worker application, which defaults to 1 GB, allocated by Juju  | {}      |
| `query_scheduler_units`                     | number      | Number of pyroscope worker units with query-scheduler role                                               | 1       |
| `query_scheduler_worker_storage_directives` | map(string) | Map of storage used by the query-scheduler worker application, which defaults to 1 GB, allocated by Juju | {}      |
| `store_gateway_units`                       | number      | Number of pyroscope worker units with store-gateway role                                                 | 1       |
| `store_gateway_worker_storage_directives`   | map(string) | Map of storage used by the store-gateway worker application, which defaults to 1 GB, allocated by Juju   | {}      |
| `tenant_settings_units`                     | number      | Number of pyroscope worker units with tenant-settings role                                               | 1       |
| `tenant_settings_worker_storage_directives` | map(string) | Map of storage used by the tenant-settings worker application, which defaults to 1 GB, allocated by Juju | {}      |
| `s3_integrator_name`                        | string      | Name of the s3-integrator app                                                                            | 1       |
| `s3_integrator_storage_directives`          | map(string) | Map of storage used by the s3-integrator application, which defaults to 1 GB, allocated by Juju          | {}      |
| `s3_bucket`                                 | string      | Name of the bucket in which pyroscope stores traces                                                      | 1       |
| `s3_access_key`                             | string      | Access key credential to connect to the S3 provider                                                      | 1       |
| `s3_secret_key`                             | string      | Secret key credential to connect to the S3 provider                                                      | 1       |
| `s3_endpoint`                               | string      | Endpoint of the S3 provider                                                                              | 1       |


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

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.5 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | >= 1.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | >= 1.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_pyroscope_ad_hoc_profiles"></a> [pyroscope\_ad\_hoc\_profiles](#module\_pyroscope\_ad\_hoc\_profiles) | ../worker/terraform | n/a |
| <a name="module_pyroscope_compactor"></a> [pyroscope\_compactor](#module\_pyroscope\_compactor) | ../worker/terraform | n/a |
| <a name="module_pyroscope_coordinator"></a> [pyroscope\_coordinator](#module\_pyroscope\_coordinator) | ../coordinator/terraform | n/a |
| <a name="module_pyroscope_distributor"></a> [pyroscope\_distributor](#module\_pyroscope\_distributor) | ../worker/terraform | n/a |
| <a name="module_pyroscope_ingester"></a> [pyroscope\_ingester](#module\_pyroscope\_ingester) | ../worker/terraform | n/a |
| <a name="module_pyroscope_querier"></a> [pyroscope\_querier](#module\_pyroscope\_querier) | ../worker/terraform | n/a |
| <a name="module_pyroscope_query_frontend"></a> [pyroscope\_query\_frontend](#module\_pyroscope\_query\_frontend) | ../worker/terraform | n/a |
| <a name="module_pyroscope_query_scheduler"></a> [pyroscope\_query\_scheduler](#module\_pyroscope\_query\_scheduler) | ../worker/terraform | n/a |
| <a name="module_pyroscope_store_gateway"></a> [pyroscope\_store\_gateway](#module\_pyroscope\_store\_gateway) | ../worker/terraform | n/a |
| <a name="module_pyroscope_tenant_settings"></a> [pyroscope\_tenant\_settings](#module\_pyroscope\_tenant\_settings) | ../worker/terraform | n/a |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_ad_hoc_profiles_name"></a> [ad\_hoc\_profiles\_name](#input\_ad\_hoc\_profiles\_name) | Name of the pyroscope ad-hoc-profiles app | `string` | `"pyroscope-ad-hoc-profiles"` | no |
| <a name="input_ad_hoc_profiles_units"></a> [ad\_hoc\_profiles\_units](#input\_ad\_hoc\_profiles\_units) | Number of pyroscope worker units with ad-hoc-profiles role | `number` | `1` | no |
| <a name="input_ad_hoc_profiles_worker_storage_directives"></a> [ad\_hoc\_profiles\_worker\_storage\_directives](#input\_ad\_hoc\_profiles\_worker\_storage\_directives) | Map of storage used by the ad-hoc-profiles worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_anti_affinity"></a> [anti\_affinity](#input\_anti\_affinity) | Enable anti-affinity constraints | `bool` | `true` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | Channel that the charms are deployed from | `string` | n/a | yes |
| <a name="input_compactor_name"></a> [compactor\_name](#input\_compactor\_name) | Name of the pyroscope compactor app | `string` | `"pyroscope-compactor"` | no |
| <a name="input_compactor_units"></a> [compactor\_units](#input\_compactor\_units) | Number of pyroscope worker units with compactor role | `number` | `1` | no |
| <a name="input_compactor_worker_storage_directives"></a> [compactor\_worker\_storage\_directives](#input\_compactor\_worker\_storage\_directives) | Map of storage used by the compactor worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_coordinator_config"></a> [coordinator\_config](#input\_coordinator\_config) | Map of the pyroscope coordinator charm configuration options | `map(string)` | `{}` | no |
| <a name="input_coordinator_revision"></a> [coordinator\_revision](#input\_coordinator\_revision) | Revision number of the coordinator charm | `number` | `null` | no |
| <a name="input_coordinator_storage_directives"></a> [coordinator\_storage\_directives](#input\_coordinator\_storage\_directives) | Map of storage used by the coordinator application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_coordinator_units"></a> [coordinator\_units](#input\_coordinator\_units) | Number of pyroscope coordinator units | `number` | `1` | no |
| <a name="input_distributor_name"></a> [distributor\_name](#input\_distributor\_name) | Name of the pyroscope distributor app | `string` | `"pyroscope-distributor"` | no |
| <a name="input_distributor_units"></a> [distributor\_units](#input\_distributor\_units) | Number of pyroscope worker units with distributor role | `number` | `1` | no |
| <a name="input_distributor_worker_storage_directives"></a> [distributor\_worker\_storage\_directives](#input\_distributor\_worker\_storage\_directives) | Map of storage used by the distributor worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_ingester_name"></a> [ingester\_name](#input\_ingester\_name) | Name of the pyroscope ingester app | `string` | `"pyroscope-ingester"` | no |
| <a name="input_ingester_units"></a> [ingester\_units](#input\_ingester\_units) | Number of pyroscope worker units with ingester role | `number` | `1` | no |
| <a name="input_ingester_worker_storage_directives"></a> [ingester\_worker\_storage\_directives](#input\_ingester\_worker\_storage\_directives) | Map of storage used by the ingester worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | Reference to an existing model resource or data source for the model to deploy to | `string` | n/a | yes |
| <a name="input_querier_name"></a> [querier\_name](#input\_querier\_name) | Name of the pyroscope querier app | `string` | `"pyroscope-querier"` | no |
| <a name="input_querier_units"></a> [querier\_units](#input\_querier\_units) | Number of pyroscope worker units with querier role | `number` | `1` | no |
| <a name="input_querier_worker_storage_directives"></a> [querier\_worker\_storage\_directives](#input\_querier\_worker\_storage\_directives) | Map of storage used by the querier worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_query_frontend_name"></a> [query\_frontend\_name](#input\_query\_frontend\_name) | Name of the pyroscope query-frontend app | `string` | `"pyroscope-query-frontend"` | no |
| <a name="input_query_frontend_units"></a> [query\_frontend\_units](#input\_query\_frontend\_units) | Number of pyroscope worker units with query-frontend role | `number` | `1` | no |
| <a name="input_query_frontend_worker_storage_directives"></a> [query\_frontend\_worker\_storage\_directives](#input\_query\_frontend\_worker\_storage\_directives) | Map of storage used by the query-frontend worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_query_scheduler_name"></a> [query\_scheduler\_name](#input\_query\_scheduler\_name) | Name of the pyroscope query-scheduler app | `string` | `"pyroscope-query-scheduler"` | no |
| <a name="input_query_scheduler_units"></a> [query\_scheduler\_units](#input\_query\_scheduler\_units) | Number of pyroscope worker units with query-scheduler role | `number` | `1` | no |
| <a name="input_query_scheduler_worker_storage_directives"></a> [query\_scheduler\_worker\_storage\_directives](#input\_query\_scheduler\_worker\_storage\_directives) | Map of storage used by the query-scheduler worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_s3_access_key"></a> [s3\_access\_key](#input\_s3\_access\_key) | S3 access-key credential | `string` | n/a | yes |
| <a name="input_s3_bucket"></a> [s3\_bucket](#input\_s3\_bucket) | Bucket name | `string` | `"pyroscope"` | no |
| <a name="input_s3_endpoint"></a> [s3\_endpoint](#input\_s3\_endpoint) | S3 endpoint | `string` | n/a | yes |
| <a name="input_s3_integrator_channel"></a> [s3\_integrator\_channel](#input\_s3\_integrator\_channel) | Channel that the s3-integrator charm is deployed from | `string` | `"2/edge"` | no |
| <a name="input_s3_integrator_name"></a> [s3\_integrator\_name](#input\_s3\_integrator\_name) | Name of the s3-integrator app | `string` | `"pyroscope-s3-integrator"` | no |
| <a name="input_s3_integrator_revision"></a> [s3\_integrator\_revision](#input\_s3\_integrator\_revision) | Revision number of the s3-integrator charm | `number` | `157` | no |
| <a name="input_s3_integrator_storage_directives"></a> [s3\_integrator\_storage\_directives](#input\_s3\_integrator\_storage\_directives) | Map of storage used by the s3-integrator application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_s3_secret_key"></a> [s3\_secret\_key](#input\_s3\_secret\_key) | S3 secret-key credential | `string` | n/a | yes |
| <a name="input_store_gateway_name"></a> [store\_gateway\_name](#input\_store\_gateway\_name) | Name of the pyroscope store-gateway app | `string` | `"pyroscope-store-gateway"` | no |
| <a name="input_store_gateway_units"></a> [store\_gateway\_units](#input\_store\_gateway\_units) | Number of pyroscope worker units with store-gateway role | `number` | `1` | no |
| <a name="input_store_gateway_worker_storage_directives"></a> [store\_gateway\_worker\_storage\_directives](#input\_store\_gateway\_worker\_storage\_directives) | Map of storage used by the store-gateway worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_tenant_settings_name"></a> [tenant\_settings\_name](#input\_tenant\_settings\_name) | Name of the pyroscope tenant-settings app | `string` | `"pyroscope-tenant-settings"` | no |
| <a name="input_tenant_settings_units"></a> [tenant\_settings\_units](#input\_tenant\_settings\_units) | Number of pyroscope worker units with tenant-settings role | `number` | `1` | no |
| <a name="input_tenant_settings_worker_storage_directives"></a> [tenant\_settings\_worker\_storage\_directives](#input\_tenant\_settings\_worker\_storage\_directives) | Map of storage used by the tenant-settings worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_worker_revision"></a> [worker\_revision](#input\_worker\_revision) | Revision number of the worker charm | `number` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_app_names"></a> [app\_names](#output\_app\_names) | n/a |
| <a name="output_provides"></a> [provides](#output\_provides) | n/a |
| <a name="output_requires"></a> [requires](#output\_requires) | n/a |
<!-- END_TF_DOCS -->