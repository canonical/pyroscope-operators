resource "juju_secret" "pyroscope_s3_credentials_secret" {
  model = var.model
  name  = "pyroscope_s3_credentials"
  value = {
    access-key = var.s3_access_key
    secret-key = var.s3_secret_key
  }
  info = "Credentials for the S3 endpoint"
}

resource "juju_access_secret" "pyroscope_s3_secret_access" {
  model = var.model
  applications = [
    juju_application.s3_integrator.name
  ]
  secret_id = juju_secret.pyroscope_s3_credentials_secret.secret_id
}

# TODO: Replace s3_integrator resource to use its remote terraform module once available
resource "juju_application" "s3_integrator" {
  name  = var.s3_integrator_name
  model = var.model
  trust = true

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
  units = 1
}

module "pyroscope_coordinator" {
  source      = "git::https://github.com/canonical/pyroscope-operators//coordinator/terraform"
  model       = var.model
  channel     = var.channel
  revision    = var.coordinator_revision
  config      = var.coordinator_config
  units       = var.coordinator_units
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=pyroscope,anti-pod.topology-key=kubernetes.io/hostname" : null
}

module "pyroscope_querier" {
  source      = "git::https://github.com/canonical/pyroscope-operators//worker/terraform"
  app_name    = var.querier_name
  model       = var.model
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.querier_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all     = false
    role-querier = true
  }
  revision = var.worker_revision
  units    = var.querier_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_query_frontend" {
  source      = "git::https://github.com/canonical/pyroscope-operators//worker/terraform"
  app_name    = var.query_frontend_name
  model       = var.model
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.query_frontend_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all            = false
    role-query-frontend = true
  }
  revision = var.worker_revision
  units    = var.query_frontend_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_ingester" {
  source      = "git::https://github.com/canonical/pyroscope-operators//worker/terraform"
  app_name    = var.ingester_name
  model       = var.model
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.ingester_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all      = false
    role-ingester = true
  }
  revision = var.worker_revision
  units    = var.ingester_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_distributor" {
  source      = "git::https://github.com/canonical/pyroscope-operators//worker/terraform"
  app_name    = var.distributor_name
  model       = var.model
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.distributor_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all         = false
    role-distributor = true
  }
  revision = var.worker_revision
  units    = var.distributor_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_compactor" {
  source      = "git::https://github.com/canonical/pyroscope-operators//worker/terraform"
  app_name    = var.compactor_name
  model       = var.model
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.compactor_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all       = false
    role-compactor = true
  }
  revision = var.worker_revision
  units    = var.compactor_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_query_scheduler" {
  source      = "git::https://github.com/canonical/pyroscope-operators//worker/terraform"
  app_name    = var.query_scheduler_name
  model       = var.model
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.query_scheduler_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all             = false
    role-query-scheduler = true
  }
  revision = var.worker_revision
  units    = var.query_scheduler_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}


module "pyroscope_store_gateway" {
  source      = "git::https://github.com/canonical/pyroscope-operators//worker/terraform"
  app_name    = var.store_gateway_name
  model       = var.model
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.store_gateway_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all           = false
    role-store-gateway = true
  }
  revision = var.worker_revision
  units    = var.store_gateway_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_tenant_settings" {
  source      = "git::https://github.com/canonical/pyroscope-operators//worker/terraform"
  app_name    = var.tenant_settings_name
  model       = var.model
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.tenant_settings_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all             = false
    role-tenant-settings = true
  }
  revision = var.worker_revision
  units    = var.tenant_settings_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

module "pyroscope_ad_hoc_profiles" {
  source      = "git::https://github.com/canonical/pyroscope-operators//worker/terraform"
  app_name    = var.ad_hoc_profiles_name
  model       = var.model
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.ad_hoc_profiles_name},anti-pod.topology-key=kubernetes.io/hostname" : null
  config = {
    role-all             = false
    role-ad-hoc-profiles = true
  }
  revision = var.worker_revision
  units    = var.ad_hoc_profiles_units
  depends_on = [
    module.pyroscope_coordinator
  ]
}

#Integrations

resource "juju_integration" "coordinator_to_s3_integrator" {
  model = var.model

  application {
    name     = juju_application.s3_integrator.name
    endpoint = "s3-credentials"
  }

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "s3"
  }
}

resource "juju_integration" "coordinator_to_querier" {
  model = var.model

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_querier.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_query_frontend" {
  model = var.model

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_query_frontend.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_ingester" {
  model = var.model

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_ingester.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_distributor" {
  model = var.model

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_distributor.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_compactor" {
  model = var.model

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_compactor.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_query_scheduler" {
  model = var.model

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_query_scheduler.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_store_gateway" {
  model = var.model

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_store_gateway.app_name
    endpoint = "pyroscope-cluster"
  }
}

resource "juju_integration" "coordinator_to_tenant_settings" {
  model = var.model

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
  model = var.model

  application {
    name     = module.pyroscope_coordinator.app_name
    endpoint = "pyroscope-cluster"
  }

  application {
    name     = module.pyroscope_ad_hoc_profiles.app_name
    endpoint = "pyroscope-cluster"
  }
}