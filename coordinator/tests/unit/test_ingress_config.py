import yaml

import traefik_config


def test_ingress_config():
    expected_ingress_config = yaml.safe_load("""
http:
  middlewares:                        
    juju-otel-pyro-middleware-noprefix:  
      stripPrefix:                    
        forceSlash: false             
        prefixes:                     
        - /otel-pyro

  routers:
    juju-otel-pyro-my-service-name:
      entryPoints:
      - my-service-name
      rule: ClientIP(`0.0.0.0/0`)
      service: juju-otel-pyro-service-my-service-name
    juju-otel-pyro-web:
      entryPoints:
      - web
      middlewares: 
      - juju-otel-pyro-middleware-noprefix
      rule: PathPrefix(`/otel-pyro`)
      service: juju-otel-pyro-service-web
  services:
    juju-otel-pyro-service-my-service-name:
      loadBalancer:
        servers:
        - url: h2c://pyro-0.pyro-endpoints.otel.svc.cluster.local:1234
    juju-otel-pyro-service-web:
      loadBalancer:
        servers:
        - url: http://pyro-0.pyro-endpoints.otel.svc.cluster.local:8080
    """)

    endpoints = [
        traefik_config.Endpoint(entrypoint_name="web", protocol="http", port=8080),
        traefik_config.Endpoint(
            entrypoint_name="my_service_name",
            protocol="grpc",
            port=1234,
        ),
    ]

    assert (
        traefik_config.ingress_config(
            endpoints,
            coordinator_fqdns=["pyro-0.pyro-endpoints.otel.svc.cluster.local"],
            model_name="otel",
            app_name="pyro",
            ingressed=True,
            tls=False,
            prefix="/otel-pyro",
        )
        == expected_ingress_config
    )


def test_static_config():
    expected_static_config = yaml.safe_load("""
    entryPoints:        
        my-service-name:      
            address: :1234 
    """)
    endpoints = [
        traefik_config.Endpoint(entrypoint_name="web", protocol="http", port=8080),
        traefik_config.Endpoint(
            entrypoint_name="my_service_name",
            protocol="grpc",
            port=1234,
        ),
    ]

    assert traefik_config.static_ingress_config(endpoints) == expected_static_config
