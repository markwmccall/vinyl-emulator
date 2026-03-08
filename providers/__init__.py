from providers.apple_music import AppleMusicProvider

_providers = {"apple": AppleMusicProvider()}


def get_provider(service_id: str):
    if service_id not in _providers:
        raise KeyError(f"Unknown music service: {service_id!r}")
    return _providers[service_id]


def list_providers() -> list:
    return list(_providers.values())
