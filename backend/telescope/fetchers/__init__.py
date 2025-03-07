from telescope.fetchers import clickhouse


def get_fetchers():
    return {
        "clickhouse": clickhouse.Fetcher,
    }
