#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'WylYeak'

import sys

reload(sys)
sys.setdefaultencoding('UTF-8')
from argparse import ArgumentParser

import requests
from bs4 import BeautifulSoup

down_type_mapper = {
    u"电驴": "ed2k",
    u"磁力": "magnet",
}


class Movie(object):
    tag = None
    file_type = None
    file_name = None
    down_map = None

    def __init__(self, tag, file_type, file_name, down_map):
        self.tag = unicode(tag)
        self.file_type = unicode(file_type)
        self.file_name = unicode(file_name)
        self.down_map = down_map
        pass

    def __str__(self):
        return "%s %s %s" % (self.tag, self.file_type, self.file_name)


def fetch_movie_info(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text)
    resource_list_list = soup.find_all("dl", "resource-list")
    for resource_list in resource_list_list:
        if len(resource_list.find_all("dt")) == 1:
            tag = resource_list.find_all("dt")[0].find("span").text
            resource_item_list = resource_list.find_all("dd", "resource-item")
            for resource_item in resource_item_list:
                file_type = resource_item.find("input", "resource-checkbox")["data-format"]
                a_list = resource_item.find_all("a")
                file_name = a_list[1].text
                download_a_list = resource_item.find("span").find_all("a")
                download_map = {}
                for download_a in download_a_list:
                    if down_type_mapper.get(download_a.text) and download_a["href"]:
                        download_map[down_type_mapper.get(download_a.text)] = download_a["href"]
                yield Movie(tag, file_type, file_name, download_map)
        else:
            print resource_list.find_all("dt")


def init_argparse():
    _parser = ArgumentParser(description="mhxz001.com movie download url")
    _parser.usage = """
    ./yyets-mhxz001.py -u http://www.mhxz001.com/file/10733 --type HR-HDTV --download_type ed2k
    """
    _parser.add_argument("-u", "--url", help="url from mhxz001.com")
    _parser.add_argument("--tag", help="tag")
    _parser.add_argument("--type", help="file_type")
    _parser.add_argument("--download_type", help="download_type " + str(down_type_mapper.values()))
    return _parser


def movie_filter(_movie, tag, file_type):
    if tag:
        if tag not in _movie.tag:
            return False
    if file_type:
        if file_type not in _movie.file_type:
            return False
    return True


if __name__ == "__main__":
    parser = init_argparse()
    args = parser.parse_args()
    assert args.url
    for movie in fetch_movie_info(args.url):
        if movie_filter(movie, args.tag, args.type):
            if args.download_type:
                print movie.down_map[args.download_type]
            else:
                print movie

