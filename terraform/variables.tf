variable "model" {
  description = "Reference to an existing model resource or data source for the model to deploy to"
  type        = string
}

variable "channel" {
  description = "Channel that the charms are deployed from"
  type        = string
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

# -------------- # App Names --------------

variable "querier_name" {
  description = "Name of the pyroscope querier app"
  type        = string
  default     = "pyroscope-querier"
}

variable "query_frontend_name" {
  description = "Name of the pyroscope query-frontend app"
  type        = string
  default     = "pyroscope-query-frontend"
}

variable "ingester_name" {
  description = "Name of the pyroscope ingester app"
  type        = string
  default     = "pyroscope-ingester"
}

variable "distributor_name" {
  description = "Name of the pyroscope distributor app"
  type        = string
  default     = "pyroscope-distributor"
}

variable "compactor_name" {
  description = "Name of the pyroscope compactor app"
  type        = string
  default     = "pyroscope-compactor"
}

variable "query_scheduler_name" {
  description = "Name of the pyroscope query-scheduler app"
  type        = string
  default     = "pyroscope-query-scheduler"
}

variable "store_gateway_name" {
  description = "Name of the pyroscope store-gateway app"
  type        = string
  default     = "pyroscope-store-gateway"
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

# -------------- # Units Per App --------------

variable "compactor_units" {
  description = "Number of pyroscope worker units with compactor role"
  type        = number
  default     = 1
  validation {
    condition     = var.compactor_units >= 1
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

variable "ingester_units" {
  description = "Number of pyroscope worker units with ingester role"
  type        = number
  default     = 1
  validation {
    condition     = var.ingester_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}

variable "query_scheduler_units" {
  description = "Number of pyroscope worker units with query-scheduler role"
  type        = number
  default     = 1
  validation {
    condition     = var.query_scheduler_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}

variable "store_gateway_units" {
  description = "Number of pyroscope worker units with store-gateway role"
  type        = number
  default     = 1
  validation {
    condition     = var.store_gateway_units >= 1
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

variable "coordinator_units" {
  description = "Number of pyroscope coordinator units"
  type        = number
  default     = 1
  validation {
    condition     = var.coordinator_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}

variable "querier_units" {
  description = "Number of pyroscope worker units with querier role"
  type        = number
  default     = 1
  validation {
    condition     = var.querier_units >= 1
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
