# Quickstart (local run)

## Prerequisites

- Install [Docker](https://www.docker.com/get-started) on your machine.

## 1. Download the Docker Image

Pull the latest Docker image from GitHub Container Registry:

```sh
docker pull ghcr.io/iamtelescope/telescope:latest
```

## 2. Copy the SQLite Database and config templates

Download the SQLite database template and config template from the repository and save it to a local folder. You can use `wget` to fetch it:

```sh
mkdir ~/.telescope/
wget -O ~/.telescope/db.sqlite3 "https://raw.githubusercontent.com/iamtelescope/telescope/refs/heads/main/dev/db.sqlite3"
wget -O ~/.telescope/config.yaml "https://raw.githubusercontent.com/iamtelescope/telescope/refs/heads/main/dev/config.yaml"
```

## 3. Start the Docker Container

Run the Docker container with the appropriate parameters:

```sh
docker run \
    -e TELESCOPE_CONFIG_FILE="/config.yaml" \
    -v $(realpath ~/.telescope/config.yaml):/config.yaml \
    -v $(realpath ~/.telescope/db.sqlite3):/db.sqlite3 \
    --network host \
    ghcr.io/iamtelescope/telescope:latest
```

Once started, the service will be available on localhost port `9898`.
Proceed to [http://localhost:9898/setup](http://localhost:9898/setup)  to create a superuser account.
