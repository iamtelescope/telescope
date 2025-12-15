from telescope.fetchers import clickhouse
from telescope.fetchers import docker
from telescope.fetchers import kubernetes
from telescope.fetchers import starrocks


def get_fetchers():
    return {
        "clickhouse": clickhouse.Fetcher,
        "docker": docker.Fetcher,
        "kubernetes": kubernetes.Fetcher,
        "starrocks": starrocks.Fetcher,
    }
