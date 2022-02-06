#!/usr/bin/env python3
import asyncio
from bs4 import BeautifulSoup, SoupStrainer
import requests
import re
import csv
import logging
import json
import functools
import psycopg2
import sys
import concurrent.futures
import os
import validators.url


logging.basicConfig(filename='./scrape/log.log', encoding='utf-8', level=logging.INFO)


MAX_THREADS = 20
OUTPUT_FILE = "./scrape/output.json"


# Gets the html of the url, strains for only <a> tags, parses them and check if any are
# applicable and return objects to be converted to json
def crawl(url):
    html = asyncio.run(get_html(url))
    # If expected return doesn't return a list the url isn't what we want
    if html:
        flag = False
        obj = {}
        multiple_found = {}
        # Only looking for <a> tags
        only_anchor = SoupStrainer("a")
        # This now only looks through only <a> tags within html
        for link in BeautifulSoup(html, "html.parser", parse_only=only_anchor):
            if link.has_attr('href'):
                # If url looks like an instance we'd like to extract
                # send url to function that will extract handle/id
                result = (expected_url(link['href']))
                if isinstance(result, list):
                    key, val = result[0], result[1]
                    if key not in obj.keys():
                        obj[key] = val
                        multiple_found[key] = [val]
                    else:
                        # If new scraped link value isn't same as old value
                        if (obj[key].lower() != val.lower()):
                            logging.warning(f"{url}: Extra {key} value found: {val}")
                            multiple_found[key].append(val)
                            flag = True
                        pass
                else:
                    pass
        if len(obj.keys()) > 0:
            obj = most_accurate(url, multiple_found) if flag else obj
            create_json(obj)
    else:
        return


# Used by above function, if multiple fb handles/twitter handles etc in
# html we check if the handle found matches the URL, and if so we pick
# that one. If not, we just choose the first option. Returns object with
# one value per key.
def most_accurate(url, obj):
    nobj = {}
    for option in obj:
        if isinstance(obj[option], list):
            for int in range(len(obj[option])):
                if (obj[option][int] in url):
                    nobj[option] = obj[option][int]
                else:
                    pass
            if option not in nobj:
                nobj[option] = obj[option][0]
        else:
            nobj[option] = obj[option]
    return (nobj)


# Regex for checking if the URL is a fb handle, twitter handle, google play store
# id, ios app store id. Returns a list, or False is it fails.
def expected_url(url):
    facebook = re.match("(?:https?:\/\/)?(?:www\.)?(?:facebook|fb|m\.facebook)\.(?:com|me)\/(?:(?:\w)*#!\/)?(?:pages\/)?(?:[\w\-]*\/)*([\w\-\.]+)(?:\/)?", url)
    if facebook:
        return ["facebook", facebook.group(1)]
    twitter = re.match("(?:https?:\/\/)?(?:www\.)?(?:twitter|mobile\.twitter).com\/([a-zA-Z0-9_]+)(?:\/)?", url)
    if twitter:
        return ["twitter", twitter.group(1)]
    google = re.match("(?:https?:\/\/)?(?:www\.)?play\.google\.com\/store\/apps\/details\?id=([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)", url)
    if google:
        return ["google", google.group(1)]
    ios = re.match("(?:https?:\/\/)?(?:www\.)?apps\.apple\.com\/[a-zA-Z]+\/app\/[a-zA-Z0-9_-]+\/id([0-9_]+)", url)
    if ios:
        return ["ios", ios.group(1)]
    else:
        return False


# Adds 'http://', if https isn't included in the URL, validates the URL,
# asynchronously runs get request for the URL (5 sec timeout) and awaits
# the result. (Requests doesn't run async natively)
async def get_html(url):
    # Handle poorly formed URLs
    quick_fix_url = url if url.startswith('http') else ('http://' + url)
    # validators.url() is a regex to check if url is valid
    if validators.url(quick_fix_url):
        loop = asyncio.get_event_loop()
        # Simulate real browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate"
        }
        try:
            # Handling timeouts
            response = loop.run_in_executor(None, functools.partial(requests.get, quick_fix_url, headers=headers, timeout=5))
            awaited = await response
            return awaited.content

        except Exception as e:
            logging.warning(f"{quick_fix_url}: {e}")
        return False
    else:
        logging.warning(f"{quick_fix_url} is not a valid URL")


def create_json(json_links):
    with open(OUTPUT_FILE, 'a') as outfile:
        json.dump(json_links, outfile, indent=4)
        outfile.write(", ")


def starting_json_file():
    with open(OUTPUT_FILE, 'a') as outfile:
        outfile.write("[")


# Removes last comma in file and adds a ']'
def finish_json_file():
    with open(OUTPUT_FILE, 'rb+') as outfile:
        outfile.seek(-2, os.SEEK_END)
        outfile.truncate()
        outfile.write(b']')


def get_csv_records(file):
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        with open(f'./scrape/{file}') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                executor.map(crawl, [row[0]])


def get_db_records(dbname, user, password, column, table):
    conn = psycopg2.connect(dbname=dbname, user=user, password=password)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {column} FROM {table}")
        for record in cursor:
            executor.map(crawl, [record[0]])


if __name__ == "__main__":
    try:
        # Has at least three args
        if len(sys.argv) > 2:
            type = sys.argv[1]
            starting_json_file()
            if type == 'db':
                print(sys.argv)
                print(len(sys.argv))
                try:
                    db_name = sys.argv[2]
                    user = sys.argv[3]
                    password = sys.argv[4]
                    column = sys.argv[5]
                    table = sys.argv[6]
                    get_db_records(db_name, user, password, column, table)
                except Exception as e:
                    logging.warning(f"Module has been called incorrectly, missing database arguments: ", e)
            elif type == 'csv':
                file = sys.argv[2]
                get_csv_records(file)
            else:
                logging.warning("Module has been called incorrectly, needs additional arguments please refer to README.md")
            finish_json_file()
        else:
            logging.warning("Module has been called incorrectly, missing additional arguments")
    except Exception as e:
        logging.warning("Module has been called incorrectly, please refer to README.md -  error: ", e)
