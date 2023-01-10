import argparse
import os
import shelve
import threading
import time

from humanize.filesize import naturalsize
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

exclude = ['/.DS_Store', '/.localized', '/desktop.ini', '$RECYCLE.BIN', '@eaDir', '/Thumbs.db']

parser = argparse.ArgumentParser(description='-s source_dir -t target_dir')
parser.add_argument('-s', '--source', required=True)
parser.add_argument('-t', '--target', required=True)
parser.add_argument('-d', '--database', required=True)
args = parser.parse_args()

source_dir = args.source
target = args.target
database = args.database

MAX_SIZE = 15 * 1024 * 1024 * 1024
print("MAX_SIZE  = ", naturalsize(MAX_SIZE))


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


def try_sync(init_size):
    linked_size = 0
    size = init_size
    for root, dirs, files in os.walk(source_dir, topdown=False, onerror=walk_error_handler):
        root = os.path.abspath(root)
        if check_exclude(root):
            print("【INFO】ignore {}".format(root))
            continue
        for f in files:
            f = os.path.join(root, f)
            if check_exclude(f):
                print("【INFO】ignore {}".format(f))
            f_size = os.path.getsize(f)
            if check_file(f):
                linked_size += f_size
                print(
                    "【INFO】skip  {} {} linked:{}".format(f, naturalsize(f_size),
                                                         naturalsize(linked_size)))
                pass
            else:
                tf = "{}".format(f).replace(source_dir, target)
                os.makedirs(os.path.dirname(tf), exist_ok=True)
                try:
                    os.link(f, tf)
                except FileExistsError as fee:
                    print("{} {} {}".format(f, tf, fee))
                    pass
                size += f_size
                linked_size += f_size
                put_file_flag(f)
                print(
                    "【INFO】link f:{} f_size:{} dest:{} linked:{}".format(f, naturalsize(f_size),
                                                                         naturalsize(size),
                                                                         naturalsize(linked_size)))
                if size > MAX_SIZE:
                    return False
        pass
    print("【INFO】 dest:{} linked:{}".format(naturalsize(size), naturalsize(linked_size)))
    return True


class EventHandler(FileSystemEventHandler):

    def __init__(self, conn, *event_types):
        self.event_types = event_types
        self.conn = conn
        pass

    def on_created(self, event):
        if "on_created" in self.event_types and not check_exclude(event.src_path):
            super().on_created(event)
            what = 'directory' if event.is_directory else 'file'
            print("【INFO】on_created {}: {}".format(what, event.src_path))
            with self.conn:
                self.conn.notifyAll()

    def on_deleted(self, event):
        if "on_deleted" in self.event_types:
            super().on_deleted(event)
            what = 'directory' if event.is_directory else 'file'
            print("【INFO】on_deleted {}: {}".format(what, event.src_path))
            with self.conn:
                self.conn.notifyAll()


target_condition = threading.Condition()
source_condition = threading.Condition()

target_handler = EventHandler(target_condition, "on_deleted")
source_handler = EventHandler(source_condition, "on_created")
observer = Observer()
observer.schedule(target_handler, target, recursive=True)
observer.schedule(source_handler, source_dir, recursive=True)
observer.start()

db = shelve.open(database)

try:
    while True:
        _size = get_dir_size(target)
        if _size > MAX_SIZE:
            print("【INFO】target full wait for notify {}".format(naturalsize(_size)))
            with target_condition:
                target_condition.wait()
            print("【INFO】target change sleep 5m for sync")
            time.sleep(5 * 60)
            continue
        if try_sync(_size):
            with source_condition:
                print("【INFO】full sync wait for notify {}".format(naturalsize(_size)))
                source_condition.wait()
                print("【INFO】source change sleep 5m for sync")
            time.sleep(5 * 60)
except KeyboardInterrupt:
    pass
db.close()
observer.stop()
observer.join()
