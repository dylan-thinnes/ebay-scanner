#!/usr/bin/env python3
import base64
import requests
import json
import subprocess
import dateutil.parser
from datetime import datetime, timezone
from enum import Enum
import sys
import time

def generate_token():
    client_id = "DylanThi-SlideRul-PRD-1aba4315e-34bf385d"
    with open("/home/dylan/ebay-client-secret", "r") as f:
        client_secret = f.read().rstrip()
    authorization = b"Basic " + base64.b64encode(bytes(client_id + ":" + client_secret, 'utf-8'))

    r = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={
            'Authorization': authorization,
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        data={
            'grant_type': "client_credentials",
            'scope': "https://api.ebay.com/oauth/api_scope"
        }
    )

    return r.json()['access_token']

def search(query, access_token, origin=None):
    r = requests.get(
        "https://api.ebay.com/buy/browse/v1/item_summary/search",
        headers={
            'Authorization': 'Bearer ' + access_token,
            'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'
        },
        params={
            'filter': 'buyingOptions:{AUCTION|FIXED_PRICE|BEST_OFFER}',
            'q': query
        }
    )

    return [make_full_item(item, origin) for item in r.json().get('itemSummaries', [])]

def item_full_data_simple(item_id, access_token, origin=None):
    return item_full_data(f'v1|{item_id}|0', access_token, origin)

def item_full_data(item_id, access_token, origin=None):
    r = requests.get(
        f"https://api.ebay.com/buy/browse/v1/item/{item_id}",
        headers={
            'Authorization': 'Bearer ' + access_token,
            'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'
        }
    )

    return make_full_item(r.json(), origin)

def make_full_item(data, origin):
    return {
        'data': data,
        'judgement': None,
        'seen': False,
        'origin': origin
    }

# All performed on ebay-items.json
def existing():
    existing_items = {}
    with open("/home/dylan/ebay-items.json", "r") as f:
        existing_items = json.load(f)
    return existing_items

def save_serialized_existing(d):
    with open("/home/dylan/ebay-items.json", "w") as f:
        json.dump(d, f, indent=2)

def append_to_existing(new_items):
    existing_items = existing()

    for new_item in new_items:
        if new_item['data']['itemId'] not in existing_items:
            existing_items[new_item['data']['itemId']] = new_item
            save_serialized_existing(existing_items)

def is_unseen(item):
    return not item['seen']

def is_alive(item):
    end_date = item['data'].get('itemEndDate')

    # If the end date is missing, it is a buy_it_now or best_offer that hasn't
    # expired, so it is interesting
    if end_date is None:
        return True

    # If the end date exists, but has not yet come to pass, the item is still
    # available, so it is interesting
    end_date = dateutil.parser.isoparse(end_date)
    now = datetime.now(timezone.utc)
    return now < end_date

def is_interesting_and_alive(item):
    # If it hasn't been seen, it is not (yet) interesting
    if is_unseen(item):
        return False

    # If it hasn't been marked 'yes', it is not (yet) interesting
    if item['judgement'] != 'y':
        return False

    return is_alive(item)

def prompt_existing():
    existing_items = existing()

    for item in existing_items.values():
        if is_unseen(item):
            proc = subprocess.Popen(
                ['surf', item['data']['itemWebUrl']],
                shell=False,
                stdin=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
            judgement = None
            while judgement not in ['y','n','u','e','r']:
                print("Judgement? [yes/no/unreachable/expensive/reconsider]")
                judgement = input()
            item['seen'] = True
            item['judgement'] = judgement
            save_serialized_existing(existing_items)
            proc.terminate()

def search_all(token=None):
    if token is None:
        token = generate_token()

    # Get query list
    with open("/home/dylan/ebay-queries.json", "r") as f:
        records = json.load(f)

    # For each group, make the queries and aggregate them
    for query_name, queries in records.items():
        for query in queries:
            print(query_name, query, file=sys.stderr, flush=True)
            origin = { 'query_name': query_name, 'query': query }
            append_to_existing(search(query, token, origin=origin))

def append_by_id(item_ids, token=None):
    if token is None:
        token = generate_token()

    for item_id in item_ids:
        origin = 'added_directly'
        item = item_full_data_simple(item_id, token, origin=origin)
        append_to_existing([item])

def summarize_existing():
    response = ''
    color = '#ffffff'
    existing_items = existing()

    with open("/home/dylan/ebay-unseen", "w") as f:
        f.write(f"")
    for item in existing_items.values():
        if is_unseen(item) and is_alive(item):
            with open("/home/dylan/ebay-unseen", "w") as f:
                f.write(f"<span color='#00ff00'>???</span>")
            break

    with open("/home/dylan/ebay-interesting", "w") as f:
        f.write(f"")
    for item in existing_items.values():
        if is_interesting_and_alive(item):
            with open("/home/dylan/ebay-interesting", "w") as f:
                f.write(f"<span color='#ff0000'>!!!</span>")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'search':
            search_all()
            summarize_existing()
        elif sys.argv[1] == 'prompt':
            prompt_existing()
            summarize_existing()
        elif sys.argv[1] == 'add':
            for item_id in sys.argv[2:]:
                append_by_id([item_id])
                summarize_existing()
        elif sys.argv[1] == 'summarize':
            summarize_existing()
        elif sys.argv[1] == 'watch':
            while True:
                print("Rerunning watch...", file=sys.stderr, flush=True)
                search_all()
                summarize_existing()
                time.sleep(600)
        elif sys.argv[1] == 'show':
            items = existing()
            subprocess.Popen(
                ['firefox'] +
                [item['data']['itemWebUrl']
                    for item in items.values()
                    if is_interesting_and_alive(item)
                ]
            )
