from telescope.fetchers import clickhouse
from telescope.fetchers import docker


def get_fetchers():
    return {
        "clickhouse": clickhouse.Fetcher,
        "docker": docker.Fetcher,
    }
