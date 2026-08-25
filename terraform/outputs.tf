output "app_names" {
  value = merge(
    {
      pyroscope_s3_integrator     = juju_application.s3_integrator.name,
      pyroscope_coordinator       = module.pyroscope_coordinator.app_name,
      pyroscope_query_frontend    = module.pyroscope_query_frontend.app_name,
      pyroscope_query_backend     = module.pyroscope_query_backend.app_name,
      pyroscope_distributor       = module.pyroscope_distributor.app_name,
      pyroscope_segment_writer    = module.pyroscope_segment_writer.app_name,
      pyroscope_metastore         = module.pyroscope_metastore.app_name,
      pyroscope_compaction_worker = module.pyroscope_compaction_worker.app_name,
      pyroscope_tenant_settings   = module.pyroscope_tenant_settings.app_name,
      pyroscope_ad_hoc_profiles   = module.pyroscope_ad_hoc_profiles.app_name,
    }
  )
}

output "provides" {
  value = {
    pyroscope_cluster = "pyroscope-cluster",
    grafana_dashboard = "grafana-dashboard",
    grafana_source    = "grafana-source",
    metrics_endpoint  = "metrics-endpoint",
  }
}

output "requires" {
  value = {
    logging            = "logging",
    ingress            = "ingress",
    certificates       = "certificates",
    send-remote-write  = "send-remote-write",
    receive_datasource = "receive-datasource",
    catalogue          = "catalogue",
    workload_tracing   = "workload-tracing",
    charm_tracing      = "charm-tracing",
    s3                 = "s3",
  }
}
