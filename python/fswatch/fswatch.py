#!/usr/bin/python
# encoding: utf-8
import argparse
import queue
import threading

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

parser = argparse.ArgumentParser(description='-s source_dir')
parser.add_argument('-s', '--source_path', required=True)
parser.add_argument('-l', '--latency', type=int, default=10, required=True)
parser.add_argument('-o', '--one_per_batch', required=False, default=False, action="store_true")
args = parser.parse_args()

source_path = args.source_path
signal = threading.Condition()
one_per_batch = args.one_per_batch


class BatchQueue:
    def __init__(self, latency):
        self.latency = latency
        self.lock = threading.RLock()
        self.queue = queue.Queue(maxsize=1000)
        self.signal = threading.Condition()
        pass

    def put(self, item):
        with self.lock:
            self.queue.put(item, block=True)

    def get_all_item(self):
        while self.queue.empty():
            with self.signal:
                self.signal.wait(self.latency)
        with self.lock:
            result_list = []
            while not self.queue.empty():
                result_list.append(self.queue.get())
            return result_list


bq = BatchQueue(args.latency)


class EventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        bq.put(event)
        pass


def worker():
    while True:
        items = bq.get_all_item()
        if one_per_batch:
            print(len(items), flush=True)
        else:
            for event in items:
                print(event)
    pass


consumer = threading.Thread(target=worker)
consumer.start()

handler = EventHandler()
observer = Observer()
observer.schedule(handler, source_path, recursive=True)
observer.start()

observer.join()
consumer.join()
