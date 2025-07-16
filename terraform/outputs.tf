output "app_names" {
  value = merge(
    {
      pyroscope_s3_integrator   = juju_application.s3_integrator.name,
      pyroscope_coordinator     = module.pyroscope_coordinator.app_name,
      pyroscope_querier         = module.pyroscope_querier.app_name,
      pyroscope_query_frontend  = module.pyroscope_query_frontend.app_name,
      pyroscope_ingester        = module.pyroscope_ingester.app_name,
      pyroscope_distributor     = module.pyroscope_distributor.app_name,
      pyroscope_compactor       = module.pyroscope_compactor.app_name,
      pyroscope_query_scheduler = module.pyroscope_query_scheduler.app_name,
      pyroscope_store_gateway   = module.pyroscope_store_gateway.app_name,
      pyroscope_tenant_settings = module.pyroscope_tenant_settings.app_name,
      pyroscope_ad_hoc_profiles = module.pyroscope_ad_hoc_profiles.app_name,
    }
  )
}

output "endpoints" {
  value = {
    # Requires
    logging            = "logging",
    ingress            = "ingress",
    certificates       = "certificates",
    send-remote-write  = "send-remote-write",
    receive_datasource = "receive-datasource",
    catalogue          = "catalogue",
    workload_tracing   = "workload-tracing",
    charm_tracing      = "charm-tracing",
    s3                 = "s3",

    # Provides
    pyroscope_cluster = "pyroscope-cluster",
    grafana_dashboard = "grafana-dashboard",
    grafana_source    = "grafana-source",
    metrics_endpoint  = "metrics-endpoint",
  }
}
