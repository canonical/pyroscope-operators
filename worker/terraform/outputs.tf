output "app_name" {
  value = juju_application.pyroscope_worker.name
}

output "provides" {
  value = {}
}

output "requires" {
  value = {
    pyroscope_cluster = "pyroscope-cluster"
  }
}