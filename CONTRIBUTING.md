# Contributing guidelines

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

I appreciate all contributions, but I would like each patch to meet certain requirements to ensure the project evolves in the right direction.

### Opening an Issue first
Before writing any code, please create an issue on GitHub for the change you are planning.
- If it’s something obvious like a typo, you can submit a direct fix without discussion.
- For bugs, provide clear reproduction steps.

### Feature Requests
For new features, I require a clear motivation for their inclusion:
- Explain the use cases this feature addresses.
- Describe why this feature is necessary.
- Discuss these points before writing any code.

I want to evaluate each feature in terms of its usefulness and alignment with my vision for the project.

### Implementation discussion for large features
If we agree that a feature is needed, I would like to discuss the implementation details—at least at a high level—before development starts.

Following these steps will help keep the project moving in the right direction according to my vision and will also prevent contributors from wasting time on changes that might not be accepted.


### Pull request target branch

Please open all pull requests against the `development` branch.

The `main` branch is reserved for stable releases and should not be the target of contributions.

### CI/CD

[CI](.github/workflows/ci.yml) runs on every push and pull request:
- backend: `black --check` and the full `pytest` suite, including the ClickHouse tests against a ClickHouse server
  loaded with the `dev/otel` test data;
- ui: `prettier --check src` and `npm run build`;
- helm: `helm lint` and `helm template`;
- docker: a build of the `Dockerfile`, without pushing.

[Release](.github/workflows/release.yml) builds the image for `linux/amd64` and `linux/arm64` and pushes it to
`ghcr.io/<owner>/<repo>` on every push to `main` and `parity` and on `v*` tags. Images are tagged with the branch name,
`sha-<short sha>`, the version for a tag (`v1.2.3` gives `1.2.3`) and `latest` for `main`. A manual run of
Release builds the image without pushing it.

To release, push a tag such as `v1.2.3`. Besides the image, this pushes the Helm chart, versioned `1.2.3`, to
`oci://ghcr.io/<owner>/charts/telescope` and creates a GitHub release with generated notes.
