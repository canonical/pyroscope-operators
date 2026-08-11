# Terraform module for pyroscope solution

This is a Terraform module facilitating the deployment of pyroscope solution, using the [Terraform juju provider](https://github.com/juju/terraform-provider-juju/). For more information, refer to the provider [documentation](https://registry.terraform.io/providers/juju/juju/latest/docs).

The solution consists of the following Terraform modules:
- [pyroscope-coordinator-k8s](https://github.com/canonical/pyroscope-operators/tree/main/coordinator): ingress, cluster coordination, single integration facade.
- [pyroscope-worker-k8s](https://github.com/canonical/pyroscope-operators/tree/main/worker): run one or more pyroscope application components.
- [s3-integrator](https://github.com/canonical/s3-integrator): facade for S3 storage configurations.

This Terraform module deploys pyroscope in its [microservices mode](https://grafana.com/docs/pyroscope/latest/reference-pyroscope-v2-architecture/about-pyroscope-v2-architecture/): each Pyroscope v2 role runs as its own worker application. The roles are `query-frontend`, `query-backend`, `distributor`, `segment-writer`, `metastore`, `compaction-worker`, `tenant-settings` and `ad-hoc-profiles`.

The `metastore` is the only stateful role: it forms a [Raft](https://raft.github.io/) quorum, so it defaults to `3` units and must always run an odd number of units. The other roles default to `1` unit and can be scaled via their `<role>_units` inputs.


> [!NOTE]
> `s3-integrator` itself doesn't act as an S3 object storage system. For the solution to be functional, `s3-integrator` needs to point to an S3-like storage. See [this guide](https://discourse.charmhub.io/t/cos-lite-docs-set-up-minio/15211) to learn how to connect to an S3-like storage for traces.

## Requirements
This module requires a `juju` model to be available. Refer to the [usage section](#usage) below for more details. See the auto-generated [Inputs](#inputs) and [Outputs](#outputs) sections below for the full list of configurable variables (per-role `*_name`, `*_units` and `*_worker_storage_directives`, plus the coordinator and s3-integrator options).

## Usage

### Basic usage

Users should ensure that Terraform is aware of the `juju_model` dependency of the charm module.

To deploy this module with its needed dependency, you can run `terraform apply -var="model_uuid=<MODEL_UUID>" -auto-approve`. This deploys all pyroscope components in the same model.

### Scaling

Stateless roles scale independently through their `<role>_units` inputs, for example `terraform apply -var="model_uuid=<MODEL_UUID>" -var="distributor_units=3"`. See [pyroscope worker roles](https://discourse.charmhub.io/t/pyroscope-worker-roles/15484) for their recommended scale.

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.5 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | >= 1.0 |

## Providers

| Name | Version |
| ---- | ------- |
| <a name="provider_juju"></a> [juju](#provider\_juju) | 2.1.1 |

## Modules

| Name | Source | Version |
| ---- | ------ | ------- |
| <a name="module_pyroscope_ad_hoc_profiles"></a> [pyroscope\_ad\_hoc\_profiles](#module\_pyroscope\_ad\_hoc\_profiles) | ../worker/terraform | n/a |
| <a name="module_pyroscope_compaction_worker"></a> [pyroscope\_compaction\_worker](#module\_pyroscope\_compaction\_worker) | ../worker/terraform | n/a |
| <a name="module_pyroscope_coordinator"></a> [pyroscope\_coordinator](#module\_pyroscope\_coordinator) | ../coordinator/terraform | n/a |
| <a name="module_pyroscope_distributor"></a> [pyroscope\_distributor](#module\_pyroscope\_distributor) | ../worker/terraform | n/a |
| <a name="module_pyroscope_metastore"></a> [pyroscope\_metastore](#module\_pyroscope\_metastore) | ../worker/terraform | n/a |
| <a name="module_pyroscope_query_backend"></a> [pyroscope\_query\_backend](#module\_pyroscope\_query\_backend) | ../worker/terraform | n/a |
| <a name="module_pyroscope_query_frontend"></a> [pyroscope\_query\_frontend](#module\_pyroscope\_query\_frontend) | ../worker/terraform | n/a |
| <a name="module_pyroscope_segment_writer"></a> [pyroscope\_segment\_writer](#module\_pyroscope\_segment\_writer) | ../worker/terraform | n/a |
| <a name="module_pyroscope_tenant_settings"></a> [pyroscope\_tenant\_settings](#module\_pyroscope\_tenant\_settings) | ../worker/terraform | n/a |

## Resources

| Name | Type |
| ---- | ---- |
| [juju_access_secret.pyroscope_s3_secret_access](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/access_secret) | resource |
| [juju_application.s3_integrator](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |
| [juju_integration.coordinator_to_ad_hoc_profiles](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.coordinator_to_compaction_worker](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.coordinator_to_distributor](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.coordinator_to_metastore](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.coordinator_to_query_backend](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.coordinator_to_query_frontend](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.coordinator_to_s3_integrator](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.coordinator_to_segment_writer](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.coordinator_to_tenant_settings](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_secret.pyroscope_s3_credentials_secret](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/secret) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_ad_hoc_profiles_name"></a> [ad\_hoc\_profiles\_name](#input\_ad\_hoc\_profiles\_name) | Name of the pyroscope ad-hoc-profiles app | `string` | `"pyroscope-ad-hoc-profiles"` | no |
| <a name="input_ad_hoc_profiles_units"></a> [ad\_hoc\_profiles\_units](#input\_ad\_hoc\_profiles\_units) | Number of pyroscope worker units with ad-hoc-profiles role | `number` | `1` | no |
| <a name="input_ad_hoc_profiles_worker_storage_directives"></a> [ad\_hoc\_profiles\_worker\_storage\_directives](#input\_ad\_hoc\_profiles\_worker\_storage\_directives) | Map of storage used by the ad-hoc-profiles worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_anti_affinity"></a> [anti\_affinity](#input\_anti\_affinity) | Enable anti-affinity constraints | `bool` | `true` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | Channel that the charms are deployed from | `string` | n/a | yes |
| <a name="input_compaction_worker_name"></a> [compaction\_worker\_name](#input\_compaction\_worker\_name) | Name of the pyroscope compaction-worker app | `string` | `"pyroscope-compaction-worker"` | no |
| <a name="input_compaction_worker_units"></a> [compaction\_worker\_units](#input\_compaction\_worker\_units) | Number of pyroscope worker units with compaction-worker role | `number` | `1` | no |
| <a name="input_compaction_worker_worker_storage_directives"></a> [compaction\_worker\_worker\_storage\_directives](#input\_compaction\_worker\_worker\_storage\_directives) | Map of storage used by the compaction-worker worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_coordinator_config"></a> [coordinator\_config](#input\_coordinator\_config) | Map of the pyroscope coordinator charm configuration options | `map(string)` | `{}` | no |
| <a name="input_coordinator_revision"></a> [coordinator\_revision](#input\_coordinator\_revision) | Revision number of the coordinator charm | `number` | `null` | no |
| <a name="input_coordinator_storage_directives"></a> [coordinator\_storage\_directives](#input\_coordinator\_storage\_directives) | Map of storage used by the coordinator application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_coordinator_units"></a> [coordinator\_units](#input\_coordinator\_units) | Number of pyroscope coordinator units | `number` | `1` | no |
| <a name="input_distributor_name"></a> [distributor\_name](#input\_distributor\_name) | Name of the pyroscope distributor app | `string` | `"pyroscope-distributor"` | no |
| <a name="input_distributor_units"></a> [distributor\_units](#input\_distributor\_units) | Number of pyroscope worker units with distributor role | `number` | `1` | no |
| <a name="input_distributor_worker_storage_directives"></a> [distributor\_worker\_storage\_directives](#input\_distributor\_worker\_storage\_directives) | Map of storage used by the distributor worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_metastore_name"></a> [metastore\_name](#input\_metastore\_name) | Name of the pyroscope metastore app | `string` | `"pyroscope-metastore"` | no |
| <a name="input_metastore_units"></a> [metastore\_units](#input\_metastore\_units) | Initial number of pyroscope worker units with metastore role. Must be odd (Raft quorum); defaults to 3 for high availability. | `number` | `3` | no |
| <a name="input_metastore_worker_storage_directives"></a> [metastore\_worker\_storage\_directives](#input\_metastore\_worker\_storage\_directives) | Map of storage used by the metastore worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | Reference to an existing model resource or data source for the model to deploy to | `string` | n/a | yes |
| <a name="input_query_backend_name"></a> [query\_backend\_name](#input\_query\_backend\_name) | Name of the pyroscope query-backend app | `string` | `"pyroscope-query-backend"` | no |
| <a name="input_query_backend_units"></a> [query\_backend\_units](#input\_query\_backend\_units) | Number of pyroscope worker units with query-backend role | `number` | `1` | no |
| <a name="input_query_backend_worker_storage_directives"></a> [query\_backend\_worker\_storage\_directives](#input\_query\_backend\_worker\_storage\_directives) | Map of storage used by the query-backend worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_query_frontend_name"></a> [query\_frontend\_name](#input\_query\_frontend\_name) | Name of the pyroscope query-frontend app | `string` | `"pyroscope-query-frontend"` | no |
| <a name="input_query_frontend_units"></a> [query\_frontend\_units](#input\_query\_frontend\_units) | Number of pyroscope worker units with query-frontend role | `number` | `1` | no |
| <a name="input_query_frontend_worker_storage_directives"></a> [query\_frontend\_worker\_storage\_directives](#input\_query\_frontend\_worker\_storage\_directives) | Map of storage used by the query-frontend worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_s3_access_key"></a> [s3\_access\_key](#input\_s3\_access\_key) | S3 access-key credential | `string` | n/a | yes |
| <a name="input_s3_bucket"></a> [s3\_bucket](#input\_s3\_bucket) | Bucket name | `string` | `"pyroscope"` | no |
| <a name="input_s3_endpoint"></a> [s3\_endpoint](#input\_s3\_endpoint) | S3 endpoint | `string` | n/a | yes |
| <a name="input_s3_integrator_channel"></a> [s3\_integrator\_channel](#input\_s3\_integrator\_channel) | Channel that the s3-integrator charm is deployed from | `string` | `"2/edge"` | no |
| <a name="input_s3_integrator_name"></a> [s3\_integrator\_name](#input\_s3\_integrator\_name) | Name of the s3-integrator app | `string` | `"pyroscope-s3-integrator"` | no |
| <a name="input_s3_integrator_revision"></a> [s3\_integrator\_revision](#input\_s3\_integrator\_revision) | Revision number of the s3-integrator charm | `number` | `157` | no |
| <a name="input_s3_integrator_storage_directives"></a> [s3\_integrator\_storage\_directives](#input\_s3\_integrator\_storage\_directives) | Map of storage used by the s3-integrator application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_s3_secret_key"></a> [s3\_secret\_key](#input\_s3\_secret\_key) | S3 secret-key credential | `string` | n/a | yes |
| <a name="input_segment_writer_name"></a> [segment\_writer\_name](#input\_segment\_writer\_name) | Name of the pyroscope segment-writer app | `string` | `"pyroscope-segment-writer"` | no |
| <a name="input_segment_writer_units"></a> [segment\_writer\_units](#input\_segment\_writer\_units) | Number of pyroscope worker units with segment-writer role | `number` | `1` | no |
| <a name="input_segment_writer_worker_storage_directives"></a> [segment\_writer\_worker\_storage\_directives](#input\_segment\_writer\_worker\_storage\_directives) | Map of storage used by the segment-writer worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_tenant_settings_name"></a> [tenant\_settings\_name](#input\_tenant\_settings\_name) | Name of the pyroscope tenant-settings app | `string` | `"pyroscope-tenant-settings"` | no |
| <a name="input_tenant_settings_units"></a> [tenant\_settings\_units](#input\_tenant\_settings\_units) | Number of pyroscope worker units with tenant-settings role | `number` | `1` | no |
| <a name="input_tenant_settings_worker_storage_directives"></a> [tenant\_settings\_worker\_storage\_directives](#input\_tenant\_settings\_worker\_storage\_directives) | Map of storage used by the tenant-settings worker application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_worker_revision"></a> [worker\_revision](#input\_worker\_revision) | Revision number of the worker charm | `number` | `null` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_app_names"></a> [app\_names](#output\_app\_names) | n/a |
| <a name="output_provides"></a> [provides](#output\_provides) | n/a |
| <a name="output_requires"></a> [requires](#output\_requires) | n/a |
<!-- END_TF_DOCS -->
