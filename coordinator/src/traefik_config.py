import dataclasses
from typing import Dict, Iterable, List, Literal, Callable


@dataclasses.dataclass
class Endpoint:
    """Represents an endpoint on the coordinator."""

    entrypoint_name: str
    protocol: Literal["http", "grpc"]
    port: int

    @property
    def sanitized_entrypoint_name(self) -> str:
        return self.entrypoint_name.replace("_", "-")


def _generate_http_routers_config(
        endpoints:Iterable[Endpoint],
        service_name_getter: Callable[[Endpoint], str],
        router_name_getter: Callable[[Endpoint], str],
        redirect_middleware_name:str,
        stripprefix_middleware_name:str,
        prefix: str
):
    http_routers = {}

    for endpoint in endpoints:
        if endpoint.protocol == "grpc":
            http_routers[router_name_getter(endpoint)] = {
                "entryPoints": [endpoint.sanitized_entrypoint_name],
                "service": service_name_getter(endpoint),
                # TODO better matcher
                "rule": "ClientIP(`0.0.0.0/0`)",
                **(
                    {"middlewares": [redirect_middleware_name]}
                    if redirect_middleware_name
                    else {}
                ),
            }

        else:
            http_routers[router_name_getter(endpoint)] = {
                "entryPoints": [endpoint.sanitized_entrypoint_name],
                "service": service_name_getter(endpoint),
                "rule": f"PathPrefix(`{prefix}`)",
                "middlewares": [stripprefix_middleware_name, *redirect_middleware_name]
            }

    return http_routers


def ingress_config(
    endpoints: Iterable[Endpoint],
    coordinator_fqdns: List[str],
    model_name: str,
    app_name: str,
    ingressed: bool,
    tls: bool,
    prefix: str,
) -> dict:
    """Build a raw ingress configuration for Traefik."""
    http_services = {}

    def middleware_name_getter(name:str):
        return f"juju-{model_name}-{app_name}-middleware-{name}"

    stripprefix_middleware_name = middleware_name_getter("stripprefix")
    middlewares = {
        stripprefix_middleware_name: {
            "stripPrefix": {"forceSlash": False, "prefixes": [prefix]}
        }
    }

    for endpoint in endpoints:
        redirect_middleware_name = middleware_name_getter(endpoint.sanitized_entrypoint_name+"-redirect")
        redirect_middleware = (
            {
                redirect_middleware_name: {
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

    def service_name_getter(endpoint: Endpoint):
        return f"juju-{model_name}-{app_name}-service-{endpoint.sanitized_entrypoint_name}"
    def router_name_getter(endpoint: Endpoint):
        return f"juju-{model_name}-{app_name}-router-{endpoint.sanitized_entrypoint_name}"

    return {
        "http": {
            "routers": _generate_http_routers_config(
                endpoints,
                service_name_getter=service_name_getter,
                router_name_getter=router_name_getter,
                stripprefix_middleware_name=stripprefix_middleware_name,
                redirect_middleware_name=redirect_middleware_name,
                prefix=prefix
            ),
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
            endpoint.entrypoint_name.replace("_", "-"): {"address": f":{endpoint.port}"}
        }
        for endpoint in endpoints
        if endpoint.protocol == "grpc"
    }
