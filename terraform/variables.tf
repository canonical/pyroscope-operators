variable "model_uuid" {
  description = "Reference to an existing model resource or data source for the model to deploy to"
  type        = string
}

variable "channel" {
  description = "Channel that the charms are deployed from"
  type        = string

  validation {
    condition     = startswith(var.channel, "dev/")
    error_message = "The track of the channel must be 'dev/'. e.g. 'dev/edge'."
  }
}

variable "s3_integrator_channel" {
  description = "Channel that the s3-integrator charm is deployed from"
  type        = string
  default     = "2/edge"
}

variable "coordinator_revision" {
  description = "Revision number of the coordinator charm"
  type        = number
  default     = null
}

variable "worker_revision" {
  description = "Revision number of the worker charm"
  type        = number
  default     = null
}

variable "s3_integrator_revision" {
  description = "Revision number of the s3-integrator charm"
  type        = number
  default     = 157 # FIXME: https://github.com/canonical/observability/issues/342
}

variable "s3_bucket" {
  description = "Bucket name"
  type        = string
  default     = "pyroscope"
}

variable "s3_access_key" {
  description = "S3 access-key credential"
  type        = string
}

variable "s3_secret_key" {
  description = "S3 secret-key credential"
  type        = string
  sensitive   = true
}

variable "s3_endpoint" {
  description = "S3 endpoint"
  type        = string
}

variable "anti_affinity" {
  description = "Enable anti-affinity constraints"
  type        = bool
  default     = true
}

variable "coordinator_config" {
  description = "Map of the pyroscope coordinator charm configuration options"
  type        = map(string)
  default     = {}
}

# -------------- # App Names --------------

variable "query_frontend_name" {
  description = "Name of the pyroscope query-frontend app"
  type        = string
  default     = "pyroscope-query-frontend"
}

variable "query_backend_name" {
  description = "Name of the pyroscope query-backend app"
  type        = string
  default     = "pyroscope-query-backend"
}

variable "distributor_name" {
  description = "Name of the pyroscope distributor app"
  type        = string
  default     = "pyroscope-distributor"
}

variable "segment_writer_name" {
  description = "Name of the pyroscope segment-writer app"
  type        = string
  default     = "pyroscope-segment-writer"
}

variable "metastore_name" {
  description = "Name of the pyroscope metastore app"
  type        = string
  default     = "pyroscope-metastore"
}

variable "compaction_worker_name" {
  description = "Name of the pyroscope compaction-worker app"
  type        = string
  default     = "pyroscope-compaction-worker"
}

variable "tenant_settings_name" {
  description = "Name of the pyroscope tenant-settings app"
  type        = string
  default     = "pyroscope-tenant-settings"
}

variable "ad_hoc_profiles_name" {
  description = "Name of the pyroscope ad-hoc-profiles app"
  type        = string
  default     = "pyroscope-ad-hoc-profiles"
}

variable "s3_integrator_name" {
  description = "Name of the s3-integrator app"
  type        = string
  default     = "pyroscope-s3-integrator"
}


# -------------- # Storage directives --------------

variable "coordinator_storage_directives" {
  description = "Map of storage used by the coordinator application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

variable "query_frontend_worker_storage_directives" {
  description = "Map of storage used by the query-frontend worker application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

variable "query_backend_worker_storage_directives" {
  description = "Map of storage used by the query-backend worker application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

variable "distributor_worker_storage_directives" {
  description = "Map of storage used by the distributor worker application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

variable "segment_writer_worker_storage_directives" {
  description = "Map of storage used by the segment-writer worker application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

variable "metastore_worker_storage_directives" {
  description = "Map of storage used by the metastore worker application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

variable "compaction_worker_worker_storage_directives" {
  description = "Map of storage used by the compaction-worker worker application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

variable "tenant_settings_worker_storage_directives" {
  description = "Map of storage used by the tenant-settings worker application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

variable "ad_hoc_profiles_worker_storage_directives" {
  description = "Map of storage used by the ad-hoc-profiles worker application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

variable "s3_integrator_storage_directives" {
  description = "Map of storage used by the s3-integrator application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

# -------------- # Units Per App --------------

variable "coordinator_units" {
  description = "Number of pyroscope coordinator units"
  type        = number
  default     = 1
  validation {
    condition     = var.coordinator_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}

variable "query_frontend_units" {
  description = "Number of pyroscope worker units with query-frontend role"
  type        = number
  default     = 1
  validation {
    condition     = var.query_frontend_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}

variable "query_backend_units" {
  description = "Number of pyroscope worker units with query-backend role"
  type        = number
  default     = 1
  validation {
    condition     = var.query_backend_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}

variable "distributor_units" {
  description = "Number of pyroscope worker units with distributor role"
  type        = number
  default     = 1
  validation {
    condition     = var.distributor_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}

variable "segment_writer_units" {
  description = "Number of pyroscope worker units with segment-writer role"
  type        = number
  default     = 1
  validation {
    condition     = var.segment_writer_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}

variable "metastore_units" {
  description = "Number of pyroscope worker units with metastore role. Must be odd (Raft quorum); defaults to 3 for high availability."
  type        = number
  default     = 3
  validation {
    condition     = var.metastore_units >= 1 && var.metastore_units % 2 == 1
    error_message = "The number of metastore units must be an odd number >= 1 (Raft quorum)."
  }
}

variable "compaction_worker_units" {
  description = "Number of pyroscope worker units with compaction-worker role"
  type        = number
  default     = 1
  validation {
    condition     = var.compaction_worker_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}

variable "tenant_settings_units" {
  description = "Number of pyroscope worker units with tenant-settings role"
  type        = number
  default     = 1
  validation {
    condition     = var.tenant_settings_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}

variable "ad_hoc_profiles_units" {
  description = "Number of pyroscope worker units with ad-hoc-profiles role"
  type        = number
  default     = 1
  validation {
    condition     = var.ad_hoc_profiles_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}
