import dataclasses
from typing import Dict, Iterable, List, Literal


@dataclasses.dataclass
class Endpoint:
    """Represents an endpoint on the coordinator."""

    name: str
    protocol: Literal["http", "grpc"]
    port: int


def ingress_config(
    endpoints: Iterable[Endpoint],
    coordinator_fqdns: List[str],
    model_name: str,
    app_name: str,
    ingressed: bool,
    tls: bool,
) -> dict:
    """Build a raw ingress configuration for Traefik."""
    http_routers = {}
    http_services = {}
    middlewares = {}
    for endpoint in endpoints:
        sanitized_endpoint_name = endpoint.name.replace("_", "-")
        redirect_middleware = (
            {
                f"juju-{model_name}-{app_name}-middleware-{sanitized_endpoint_name}": {
                    "redirectScheme": {
                        "permanent": True,
                        "port": endpoint.port,
                        "scheme": "https",
                    }
                }
            }
            if ingressed and tls
            else {}
        )
        middlewares.update(redirect_middleware)

        http_routers[f"juju-{model_name}-{app_name}-{sanitized_endpoint_name}"] = {
            "entryPoints": [sanitized_endpoint_name],
            "service": f"juju-{model_name}-{app_name}-service-{sanitized_endpoint_name}",
            # TODO better matcher
            "rule": "ClientIP(`0.0.0.0/0`)",
            **(
                {"middlewares": list(redirect_middleware.keys())}
                if redirect_middleware
                else {}
            ),
        }
        if endpoint.protocol == "grpc" and not tls:
            # to send data to unsecured GRPC endpoints, we need h2c
            # see https://doc.traefik.io/traefik/v2.0/user-guides/grpc/#with-http-h2c
            http_services[
                f"juju-{model_name}-{app_name}-service-{sanitized_endpoint_name}"
            ] = {
                "loadBalancer": {
                    "servers": _build_lb_server_config(
                        "h2c", endpoint.port, coordinator_fqdns
                    )
                }
            }
        else:
            # anything else, including secured GRPC, can use _internal_url
            # ref https://doc.traefik.io/traefik/v2.0/user-guides/grpc/#with-https
            http_services[
                f"juju-{model_name}-{app_name}-service-{sanitized_endpoint_name}"
            ] = {
                "loadBalancer": {
                    "servers": _build_lb_server_config(
                        "https" if tls else "http", endpoint.port, coordinator_fqdns
                    )
                }
            }

    return {
        "http": {
            "routers": http_routers,
            "services": http_services,
            # else we get: level=error msg="Error occurred during watcher callback:
            # ...: middlewares cannot be a standalone element (type map[string]*dynamic.Middleware)"
            # providerName=file
            **({"middlewares": middlewares} if middlewares else {}),
        }
    }


def _build_lb_server_config(
    scheme: str, port: int, coordinator_fqdns: List[str]
) -> List[Dict[str, str]]:
    """build the server portion of the loadbalancer config of Traefik ingress."""
    return [{"url": f"{scheme}://{fqdn}:{port}"} for fqdn in coordinator_fqdns]


def static_ingress_config(endpoints: List[Endpoint]):
    """Static portion of the traefik-route ingress configuration."""
    return {
        "entryPoints": {
            endpoint.name.replace("_", "-"): {"address": f":{endpoint.port}"}
        }
        for endpoint in endpoints
    }
