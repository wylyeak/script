#!/usr/bin/python
# encoding: utf-8
import argparse
import logging.config
import os
import shelve
import threading
import time

import requests
from humanize.filesize import naturalsize
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logging.config.fileConfig(os.path.join(os.path.dirname(__file__), 'logging.conf'))
logger = logging.getLogger()

exclude = ['/.DS_Store', '/.localized', '/desktop.ini', '$RECYCLE.BIN', '@eaDir', '/Thumbs.db']

parser = argparse.ArgumentParser(description='-s source_dir -t target_dir')
parser.add_argument('-s', '--source', required=True)
parser.add_argument('-t', '--target', required=True)
parser.add_argument('-d', '--database', required=True)
parser.add_argument('-n', '--dry', required=False, default=False, action="store_true")
parser.add_argument('-pk', '--push_key', required=False)
args = parser.parse_args()

source_dir = args.source
target = args.target
database = args.database
debug = args.dry
push_key = args.push_key

MAX_SIZE = 15 * 1024 * 1024 * 1024
logger.info("MAX_SIZE  = %s", naturalsize(MAX_SIZE))


def check_exclude(f):
    for e in exclude:
        if e in f:
            return True
    return False


def put_file_flag(f):
    db["{}".format(f)] = True
    db.sync()


def bark_push(title, body):
    if not push_key:
        return False
    json_data = {
        "body": body,
        "title": title
    }
    resp = requests.post("https://api.day.app/{}".format(push_key), json=json_data)
    r = resp.json()
    if r["code"] == 200:
        return True
    else:
        logger.error("push error, msg=%s, title=%s body=%s", r["message"], title, body)
    pass


def check_file(f):
    return "{}".format(f) in db


def walk_error_handler(ex):
    logger.exception(ex)


def get_dir_size(top):
    size = 0
    for root, dirs, files in os.walk(top, topdown=False, onerror=walk_error_handler):
        root = os.path.abspath(root)
        for f in files:
            f = os.path.join(root, f)
            size += os.path.getsize(f)
    return size


def try_sync(init_size):
    total_linked_size = 0
    size = init_size
    total_linked_num = 0
    curr_link_num = 0
    for root, dirs, files in os.walk(source_dir, topdown=False, onerror=walk_error_handler):
        root = os.path.abspath(root)
        if check_exclude(root):
            logger.info("ignore {}".format(root))
            continue
        for f in files:
            f = os.path.join(root, f)
            if check_exclude(f):
                logger.info("ignore {}".format(f))
            f_size = os.path.getsize(f)
            if check_file(f):
                total_linked_size += f_size
                total_linked_num += 1
                logger.info(
                    "skip  {} {} linked:{}".format(f, naturalsize(f_size),
                                                   naturalsize(total_linked_size)))
                pass
            else:
                tf = "{}".format(f).replace(source_dir, target)
                os.makedirs(os.path.dirname(tf), exist_ok=True)
                try:
                    if not debug:
                        os.link(f, tf)
                        put_file_flag(f)
                    total_linked_num += 1
                    curr_link_num += 1
                    size += f_size
                    total_linked_size += f_size
                    logger.info(
                        "link f:{} f_size:{} dest:{} linked:{}".format(f, naturalsize(f_size),
                                                                       naturalsize(size),
                                                                       naturalsize(total_linked_size)))
                    if size > MAX_SIZE:
                        bark_push('文件同步', "当前同步{}个共{},总同步{}个共{}".format(curr_link_num, naturalsize(size),
                                                                                       total_linked_num,
                                                                                       naturalsize(total_linked_size)))
                        return False
                except FileExistsError as fee:
                    logger.error("{} {} {}".format(f, tf, fee))
                    pass
        pass
    logger.info("当前同步{}个共{},总同步{}个共{}".format(curr_link_num, naturalsize(size), total_linked_num,
                                                         naturalsize(total_linked_size)))
    bark_push('文件同步', "当前同步{}个共{},总同步{}个共{}".format(curr_link_num, naturalsize(size), total_linked_num,
                                                                   naturalsize(total_linked_size)))
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
            logger.info("on_created {}: {}".format(what, event.src_path))
            with self.conn:
                self.conn.notifyAll()

    def on_deleted(self, event):
        if "on_deleted" in self.event_types:
            super().on_deleted(event)
            what = 'directory' if event.is_directory else 'file'
            logger.info("on_deleted {}: {}".format(what, event.src_path))
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
            logger.info("target full wait for notify {}".format(naturalsize(_size)))
            with target_condition:
                target_condition.wait()
            logger.info("target change sleep 5m for sync")
            time.sleep(5 * 60)
            continue
        if try_sync(_size):
            with source_condition:
                logger.info("full sync wait for notify {}".format(naturalsize(_size)))
                source_condition.wait()
                logger.info("source change sleep 5m for sync")
            time.sleep(5 * 60)
except KeyboardInterrupt:
    pass
db.close()
observer.stop()
observer.join()
