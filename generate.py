"""
USP Test Cassette Generator
Copyright (C) 2024 Freddy Heppell and The University of Sheffield.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import argparse
from datetime import datetime
import gzip
import hashlib
import json
import logging
from pathlib import Path
import re
import shutil
from urllib.parse import urlparse
from importlib.metadata import PackageNotFoundError, version
from usp.tree import sitemap_tree_for_homepage
import vcr
import sh

def test_gh():
    try:
        sh.gh.auth.status(hostname="github.com", _tty_out=False)
    except sh.CommandNotFound:
        logging.error("gh command not found. The GitHub CLI must be installed and available to use auto-uploading")
        exit(1)
    except sh.ErrorReturnCode_1:
        logging.error("It appears you are not logged into the GitHub CLI. Run `gh auth status` to check this.")
        exit(1)
    return


def save_cassette(url, out_path):
    with vcr.use_cassette(str(out_path), record_on_exception=False):
        sitemap_tree_for_homepage(url)

def compress_file(path: Path):
    gzip_path = path.with_suffix(path.suffix + '.gz')

    with open(path, "rb") as f, gzip.open(gzip_path, "wb") as g:
        shutil.copyfileobj(f, g)

    with open(gzip_path, "rb") as g:
        gzip_hash = hashlib.sha256(g.read()).hexdigest()

    return gzip_path, gzip_hash

def get_usp_version():
    try:
        self_reported = version('ultimate-sitemap-parser')
    except PackageNotFoundError:
        self_reported = "Unable to detect"

    pip_frozen = sh.pip("freeze", _tty_out=False)
    commit_hash_match = re.search(r"ultimate-sitemap-parser\.git@(\w+)", pip_frozen)

    if commit_hash_match:
        commit_hash = commit_hash_match.group(1)
    else:
        commit_hash = "Unable to detect"

    return self_reported, commit_hash


def make_release_notes(url, datetime):
    v_self,v_pip = get_usp_version()
    dt_formatted = datetime.isoformat()
    return f"USP Test Cassette generated for `{url}` at {dt_formatted}.\n\n" + \
              f"USP Self-Reported Version: `{v_self}`\n\n" + \
              f"USP Pip Commit: `{v_pip}`\n"

def create_release(url, domain):
    release_name = f"{domain} Sitemap Cassette"
    now_time = datetime.now()
    tag_name = now_time.strftime("%Y%m%d%H%M%S") + f"-{domain}"
    notes = make_release_notes(url, now_time)
    sh.gh.release.create(tag_name, title=release_name, latest='False', notes=notes, _tty_out=False)
    return tag_name

def upload_asset(release_tag, asset_path):
    sh.gh.release.upload(release_tag, asset_path)

def get_assets(release_tag):
    out = sh.gh.release.view(release_tag, json="assets", _tty_out=False)
    return json.loads(out)["assets"]

def load_manifest():
    with open('manifest.json', 'r') as f:
        return json.load(f)


def update_manifest(manifest, url, out_file_name, asset_url, asset_hash):
    manifest[url] = {
        "name": out_file_name,
        "url": asset_url,
        "hash": asset_hash
    }

    with open('manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="URL to download")
    parser.add_argument("--upload", action="store_true")
    parser.set_defaults(upload=False)
    args = parser.parse_args()

    if args.upload:
        test_gh()

    url = args.url
    if not url.endswith("/"):
        url += "/"

    url_parsed = urlparse(url)
    domain = url_parsed.netloc

    out_file_name = f"{domain}.yaml"
    out_path = Path("out") / out_file_name
    out_path.parent.mkdir(exist_ok=True)

    save_cassette(args.url, out_path)
    logging.info(f"Saving to {out_path.resolve()}")

    if not args.upload:
        exit(0)

    compressed_path, compressed_hash = compress_file(out_path)

    manifest = load_manifest()

    if manifest.get(url, {}).get('hash', None) == compressed_hash:
        logging.info("Cassette unchanged, skipping upload")
        exit(0)

    tag = create_release(url, domain)
    upload_asset(tag, compressed_path)
    cassette_asset = get_assets(tag)[0]
    logging.info(f"New cassette uploaded to {cassette_asset['url']}")
    update_manifest(manifest, url, out_file_name, cassette_asset["url"], compressed_hash)
    logging.info(f"Updated and saved manifest")