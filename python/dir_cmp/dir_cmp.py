#!/usr/bin/python
# encoding: utf-8
import argparse
import hashlib
import os

exclude = ['/.DS_Store', '/.localized', '/desktop.ini', '$RECYCLE.BIN', '@eaDir', '/Thumbs.db']

parser = argparse.ArgumentParser(description='-o origin_dir -d target_dir')
parser.add_argument('-o', '--origin_dir', required=True)
parser.add_argument('-d', '--dest_dir', required=True)
parser.add_argument('--quiet', action='store_true')
args = parser.parse_args()

origin_dir = args.origin_dir
dest_dir = args.dest_dir
quiet = args.quiet


def check_sha256(filename1, filename2):
    h1 = get_sha256(filename1)
    h2 = get_sha256(filename2)
    return h1 == h2


def get_sha256(filename):
    h = hashlib.sha256()
    with open(filename, 'rb') as fh:
        while True:
            data = fh.read(4096)
            if len(data) == 0:
                break
            h.update(data)
    return h.hexdigest()


def check_exclude(f):
    for e in exclude:
        if e in f:
            return True
    return False


def walk_error_handler(ex):
    print(ex)


def log(msg):
    if not quiet:
        print(msg)


ignore = 0
full_match = 0
not_match = 0
for root, dirs, files in os.walk(origin_dir, topdown=False, onerror=walk_error_handler):
    root = os.path.abspath(root)
    if check_exclude(root):
        log("[INFO] ignore {}".format(root))
        ignore += 1
        continue
    for f in files:
        f = os.path.join(root, f)
        if check_exclude(f):
            log("[INFO] ignore {}".format(f))
            ignore += 1
            continue
        tf = "{}".format(f).replace(origin_dir, dest_dir)
        if not os.path.exists(tf):
            print("[WARN] notExists {} -> {}".format(f, tf))
            not_match += 1
            continue
        if not check_sha256(f, tf):
            print("[WARN] notMatch {} -> {}".format(f, tf))
            not_match += 1
            continue
        log("[INFO] fullMatch {}->{}".format(f, tf))
        full_match += 1
    pass
print("[INFO] ignore:{} full_match:{} not_match:{}".format(ignore, full_match, not_match))
