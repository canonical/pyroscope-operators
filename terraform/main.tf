resource "juju_secret" "pyroscope_s3_credentials_secret" {
  model_uuid = var.model_uuid
  name       = "pyroscope_s3_credentials"
  value = {
    access-key = var.s3_access_key
    secret-key = var.s3_secret_key
  }
  info = "Credentials for the S3 endpoint"
}

resource "juju_access_secret" "pyroscope_s3_secret_access" {
  model_uuid = var.model_uuid
  applications = [
    juju_application.s3_integrator.name
  ]
  secret_id = juju_secret.pyroscope_s3_credentials_secret.secret_id
}

# TODO: Replace s3_integrator resource to use its remote terraform module once available
resource "juju_application" "s3_integrator" {
  name       = var.s3_integrator_name
  model_uuid = var.model_uuid
  trust      = true

  charm {
    name     = "s3-integrator"
    channel  = var.s3_integrator_channel
    revision = var.s3_integrator_revision
  }
  config = {
    endpoint    = var.s3_endpoint
    bucket      = var.s3_bucket
    credentials = "secret:${juju_secret.pyroscope_s3_credentials_secret.secret_id}"
  }
  storage_directives = var.s3_integrator_storage_directives
  units              = 1
}

module "pyroscope_coordinator" {
  source             = "../coordinator/terraform"
  model_uuid         = var.model_uuid
  channel            = var.channel
  revision           = var.coordinator_revision
  config             = var.coordinator_config
  storage_directives = var.coordinator_storage_directives
  units              = var.coordinator_units
  constraints        = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=pyroscope,anti-pod.topology-key=kubernetes.io/hostname" : null
}

module "pyroscope_query_frontend" {
  source      = "../worker/terraform"
  app_name    = var.query_frontend_name
  model_uuid  = var.model_uuid
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.query_frontend_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all            = false
    role-query-frontend = true
  }
  revision           = var.worker_revision
  storage_directives = var.query_frontend_worker_storage_directives
  units              = var.query_frontend_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_query_backend" {
  source      = "../worker/terraform"
  app_name    = var.query_backend_name
  model_uuid  = var.model_uuid
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.query_backend_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all           = false
    role-query-backend = true
  }
  revision           = var.worker_revision
  storage_directives = var.query_backend_worker_storage_directives
  units              = var.query_backend_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_distributor" {
  source      = "../worker/terraform"
  app_name    = var.distributor_name
  model_uuid  = var.model_uuid
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.distributor_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all         = false
    role-distributor = true
  }
  revision           = var.worker_revision
  storage_directives = var.distributor_worker_storage_directives
  units              = var.distributor_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_segment_writer" {
  source      = "../worker/terraform"
  app_name    = var.segment_writer_name
  model_uuid  = var.model_uuid
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.segment_writer_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all            = false
    role-segment-writer = true
  }
  revision           = var.worker_revision
  storage_directives = var.segment_writer_worker_storage_directives
  units              = var.segment_writer_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

# The metastore is the only stateful v2 component. It forms a Raft quorum, so it
# defaults to 3 units for high availability (an odd count avoids split-brain).
module "pyroscope_metastore" {
  source      = "../worker/terraform"
  app_name    = var.metastore_name
  model_uuid  = var.model_uuid
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.metastore_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all       = false
    role-metastore = true
  }
  revision           = var.worker_revision
  storage_directives = var.metastore_worker_storage_directives
  units              = var.metastore_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_compaction_worker" {
  source      = "../worker/terraform"
  app_name    = var.compaction_worker_name
  model_uuid  = var.model_uuid
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.compaction_worker_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all               = false
    role-compaction-worker = true
  }
  revision           = var.worker_revision
  storage_directives = var.compaction_worker_worker_storage_directives
  units              = var.compaction_worker_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_tenant_settings" {
  source      = "../worker/terraform"
  app_name    = var.tenant_settings_name
  model_uuid  = var.model_uuid
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.tenant_settings_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all             = false
    role-tenant-settings = true
  }
  revision           = var.worker_revision
  storage_directives = var.tenant_settings_worker_storage_directives
  units              = var.tenant_settings_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_ad_hoc_profiles" {
  source      = "../worker/terraform"
  app_name    = var.ad_hoc_profiles_name
  model_uuid  = var.model_uuid
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.ad_hoc_profiles_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all             = false
    role-ad-hoc-profiles = true
  }
  revision           = var.worker_revision
  storage_directives = var.ad_hoc_profiles_worker_storage_directives
  units              = var.ad_hoc_profiles_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

#Integrations

resource "juju_integration" "coordinator_to_s3_integrator" {
  model_uuid = var.model_uuid

  application {
    name     = juju_application.s3_integrator.name
    endpoint = "s3-credentials"
  }

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "s3"
  }
}

resource "juju_integration" "coordinator_to_query_frontend" {
  model_uuid = var.model_uuid

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_query_frontend.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_query_backend" {
  model_uuid = var.model_uuid

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_query_backend.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_distributor" {
  model_uuid = var.model_uuid

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_distributor.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_segment_writer" {
  model_uuid = var.model_uuid

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_segment_writer.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_metastore" {
  model_uuid = var.model_uuid

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_metastore.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_compaction_worker" {
  model_uuid = var.model_uuid

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_compaction_worker.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_tenant_settings" {
  model_uuid = var.model_uuid

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_tenant_settings.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_ad_hoc_profiles" {
  model_uuid = var.model_uuid

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_ad_hoc_profiles.app_name
    endpoint = "pyroscope-cluster"
  }
}
