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

MAX_THREADS = 20

conn = psycopg2.connect(
    dbname='urls', user='awallis', password='admin'
)

logging.basicConfig(filename='./scrape/log.log', encoding='utf-8', level=logging.INFO)


def crawl(url):
    html = asyncio.run(get_html(url))
    # If expected return doesn't return a list the url isn't what we want
    if html:
        flag = False
        obj = {}
        multiple_found = {}
        only_anchor = SoupStrainer("a")
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
                            logging.warning(f"{url}: Extra {key} value found: {val}, current value is {obj[key]}") 
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


def expected_url(url):
    # Does it have the url expected of a Twitter handle/Google Play
    # /Facebook Page id/IOS app store id
    facebook = re.match("(?:https?:\/\/)?(?:www\.)?(?:facebook|fb|m\.facebook)\.(?:com|me)\/(?:(?:\w)*#!\/)?(?:pages\/)?(?:[\w\-]*\/)*([\w\-\.]+)(?:\/)?", url)
    twitter = re.match("(?:https?:\/\/)?(?:www\.)?twitter.com\/(?![a-zA-Z0-9_]+\/)([a-zA-Z0-9_]+)", url)
    google = re.match("(?:https?:\/\/)?(?:www\.)?play\.google\.com\/store\/apps\/details\?id=([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)", url)
    ios = re.match("(?:https?:\/\/)?(?:www\.)?apps\.apple\.com\/[a-zA-Z]+\/app\/[a-zA-Z0-9_-]+\/id([0-9_]+)", url)

    # Could hardcode in facebook: facebook for facebook.com
    if facebook:
        return ["facebook", facebook.group(1)]
    # Could hardcode in twitter: twitter for twitter.com
    elif twitter:
        return ["twitter", twitter.group(1)]
    elif google:
        return ["google", google.group(1)]
    elif ios:
        return ["ios", ios.group(1)]
    else:
        return False


async def get_html(url):
    # Handle poorly formed URLs
    quick_fix_url = url if url.startswith('http') else ('http://' + url)
    loop = asyncio.get_event_loop()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36',
        "Upgrade-Insecure-Requests": "1", "DNT": "1",
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
    

def create_json(json_links):
    with open("./scrape/output.json", 'a') as outfile:
        json.dump(json_links, outfile, indent=4)
        outfile.write(", ")


def starting_json_file():
    with open("./scrape/output.json", 'a') as outfile:
        outfile.write("[")


def remove_last_comma():
    with open("./scrape/output.json", 'rb+') as filehandle:
        filehandle.seek(-2, os.SEEK_END)
        filehandle.truncate() 


def finish_json_file():
    with open("./scrape/output.json", 'a') as outfile:
        outfile.write("]")


def get_csv_records(file):
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        with open(f'./scrape/{file}') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                executor.map(crawl, [row[0]])
    

def get_db_records():
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        cursor = conn.cursor()
        cursor.execute("SELECT url FROM scraped_urls")
        for record in cursor:
            executor.map(crawl, [record[0]])


if __name__ == "__main__":
    try: 
        type = sys.argv[1]
        starting_json_file()
        if type == 'db':
            get_db_records()
        elif type == 'csv':
            file = sys.argv[2] 
            get_csv_records(file)
        else:
            logging.warning(f"Incorrect argument chosen, must be either 'db' or 'csv'") 
        
        remove_last_comma()
        finish_json_file()
    except Exception:
        logging.warn("Module has been called incorrectly")
