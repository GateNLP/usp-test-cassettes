# Ultimate Sitemap Parser Test Cassettes

This repository generates the [VCR.py](https://vcrpy.readthedocs.io/) cassettes for Ultimate Sitemap Parser's integration and performance tests.

Cassettes are recordings of HTTP requests and responses which mean the tests can run faster and without causing excessive strain to servers.

**If you just want to run the integration and performance tests of Ultimate Sitemap Parser, you don't need to use this repository directly.** Within the main repository for USP there are scripts to download cassette files.

## Cassette Generation and Distribution

Prerequisites:

- Install the environment through Poetry 

To upload cassettes for sharing, you will also need:
  - The [GitHub CLI](https://cli.github.com/), signed in to an account with write access to this repo

Cassettes are generated through the following process:

1. Run `python generate.py [--upload] https://example.org`
2. USP is run within a VCR.py context to record and save HTTP requests and responses
3. The VCR cassette is saved to `out/example.org.yaml`
    * If the `--upload` argument is omitted, the program stops here
4. The cassette is gzipped to `out/example.org.yaml.gz` and hash calculated
    * If the hash is the same as the version in the manifest, the program stops here
5. A new GitHub release is created with the tag `yyyymmddhhmmss-example.org`
6. `example.org.yaml.gz` is attached to the release as an asset
7. The download URL of the asset and its hash are updated in `manifest.json`
8. Now commit and push the new version of `manifest.json`
