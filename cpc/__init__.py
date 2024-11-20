#!/usr/bin/env python3
import os
import shutil
import sys
import re
import subprocess
import tempfile
from urllib.parse import urlparse
from pathlib import Path
from typing import List
import argparse

def is_url(s: str) -> bool:
    try:
        result = urlparse(s)
        return result.scheme in ('http', 'https', 'ftp')
    except:
        return False

def is_remote_path(s: str) -> bool:
    return re.match(r'^(?:[a-zA-Z0-9_.-]+@)?[a-zA-Z0-9_.-]+:.+', s) is not None

def execute_command(command: List[str]):
    print("Executing command: {}".format(' '.join(command)))
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print("Error executing command: {}".format(' '.join(command)))
        sys.exit(e.returncode)

def download_http(src: str, dst: str, extra_opts: List[str]):
    dst_path = Path(dst)
    if dst_path.is_dir():
        command: List[str] = ['curl', '-OJL', src] + ['--output-dir', str(dst_path)] + extra_opts
    else:
        command: List[str] = ['curl', '-L', src, '-o', str(dst_path)] + extra_opts
    execute_command(command)

def copy_remote(src: str, dst: str, extra_opts: List[str]):
    command: List[str] = ['rsync', '-a', '--info=progress2'] + extra_opts + [src, dst]
    execute_command(command)

def copy_local(src: str, dst: str, extra_opts: List[str]):
    command: List[str] = ['rsync', '-a'] + extra_opts + [src, dst]
    execute_command(command)

def handle_extract(src: str, dst: str):
    src_path = Path(src)
    dst_path = Path(dst)
    if not src_path.is_file():
        print(f"Error: copied file is not valid")
        sys.exit(1)
    command: List[str] = ['atool', str(src_path), '--extract-to', dst]
    execute_command(command)

def handle_spill(dst: str):
    path = Path(dst)
    spill_dir = path.parent
    while path.is_dir():
        contents = list(path.iterdir())
        if len(contents) != 1:
            shutil.copytree(path, spill_dir, dirs_exist_ok=True)
            break
        content: Path = contents[0]
        path = content.rename(spill_dir / content.name)

def main() -> None:
    cmd_name: str = Path(sys.argv[0]).name
    should_extract: bool = cmd_name.startswith('cpx')
    should_dig: bool = cmd_name.endswith('d')

    parser = argparse.ArgumentParser(
      prog=cmd_name,
      description="Copy files from SRC to DST with optional arguments."
    )
    parser.add_argument('src', type=str, help='Source path or URL')
    parser.add_argument('dst', type=str, nargs='?', default='./', help='Destination path')
    parser.add_argument('extra_opts', nargs=argparse.REMAINDER, help='Additional options for the copy command')
    args = parser.parse_args()
    src, dst, extra_opts =  args.src, args.dst, args.extra_opts
    assert isinstance(src, str) and isinstance(dst, str) and isinstance(extra_opts, list)

    try:
        tmp_archive, actual_dest = None, None
        if should_extract:
            tmp_archive = tempfile.mktemp()
            dst, actual_dest = tmp_archive, dst

        if is_url(src):
            download_http(src, dst, extra_opts)
        elif is_remote_path(src) or is_remote_path(dst):
            copy_remote(src, dst, extra_opts)
        else:
            copy_local(src, dst, extra_opts)

        if should_extract:
            assert tmp_archive is not None and actual_dest is not None
            handle_extract(tmp_archive, actual_dest)
            dst = actual_dest
    
        if should_dig:
            handle_spill(dst)
    finally:
        if tmp_archive is not None:
            os.unlink(tmp_archive)


if __name__ == '__main__':
    main()
