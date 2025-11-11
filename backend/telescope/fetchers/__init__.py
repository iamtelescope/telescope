from telescope.fetchers import clickhouse
from telescope.fetchers import docker
from telescope.fetchers import kubernetes


def get_fetchers():
    return {
        "clickhouse": clickhouse.Fetcher,
        "docker": docker.Fetcher,
        "kubernetes": kubernetes.Fetcher,
    }
