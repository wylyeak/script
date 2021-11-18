import argparse
import os
import shelve
import time

import humanize

exclude = ['/.DS_Store', '/.localized', '/desktop.ini', '$RECYCLE.BIN', '@eaDir']

parser = argparse.ArgumentParser(description='-s source_dir -t target_dir')
parser.add_argument('-s', '--source', required=True)
parser.add_argument('-t', '--target', required=True)
args = parser.parse_args()

source_dir = args.source
target = args.target

MAX_SIZE = 15 * 1024 * 1024 * 1024
print("MAX_SIZE  = ", humanize.filesize.naturalsize(MAX_SIZE, gnu=True))


def check_exclude(f):
    for e in exclude:
        if e in f:
            return True
    return False


def put_file_flag(f):
    db["{}".format(f)] = True
    db.sync()


def check_file(f):
    return "{}".format(f) in db


def walk_error_handler(ex):
    print(ex)


def get_dir_size(top):
    size = 0
    for root, dirs, files in os.walk(top, topdown=False, onerror=walk_error_handler):
        root = os.path.abspath(root)
        for f in files:
            f = os.path.join(root, f)
            size += os.path.getsize(f)
    return size


def try_sync():
    size = get_dir_size(target)
    if size > MAX_SIZE:
        print("【INFO】{} sleep 3600s".format(humanize.filesize.naturalsize(size, gnu=True)))
        time.sleep(3600)
        return False
    for root, dirs, files in os.walk(source_dir, topdown=False, onerror=walk_error_handler):
        root = os.path.abspath(root)
        if check_exclude(root):
            print("【INFO】ignore {}".format(root))
            continue
        for f in files:
            f = os.path.join(root, f)
            if check_exclude(f):
                print("【INFO】ignore {}".format(f))
            if check_file(f):
                print("【INFO】skip  {}".format(f))
                pass
            else:
                tf = "{}".format(f).replace(source_dir, target)
                os.makedirs(os.path.dirname(tf), exist_ok=True)
                os.link(f, tf)
                size += os.path.getsize(f)
                put_file_flag(f)
                print("【INFO】link {} {}".format(f, humanize.filesize.naturalsize(size, gnu=True)))
                if size > MAX_SIZE:
                    return False
        pass
    print("【INFO】 {}".format(humanize.filesize.naturalsize(size, gnu=True)))
    return True


home_dir = os.path.expanduser("~")
db_file = os.path.join(home_dir, "shelve")
db = shelve.open(db_file)

try:
    while True:
        if try_sync():
            break
except KeyboardInterrupt:
    db.close()
    pass
