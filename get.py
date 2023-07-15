import bs4
import sys
import requests
import urllib.parse
import json
from datetime import datetime
import re
from dateutil.relativedelta import relativedelta

def search_endpoint(phrase, completed=False):
    params = [("_nkw", phrase)]
    if completed:
        params.append(("LH_Complete","1"))
        params.append(("LH_Sold","1"))
    param_string = urllib.parse.urlencode(params)
    return f"https://www.ebay.com/sch/i.html?{param_string}"

def search(phrase, completed=False):
    res = requests.get(search_endpoint(phrase, completed))
    if res.status_code == 200:
        return bs4.BeautifulSoup(res.content, features="lxml")
    return None

def get_exact_items(soup):
    rewrite_start = soup.find(class_="srp-river-answer--REWRITE_START")
    if rewrite_start == None:
        all_results = soup.find(id="srp-river-results")
        return all_results.findAll(class_="s-item")
    else:
        return rewrite_start.findPreviousSiblings(class_="s-item")

def extract_purchase_type(phrase, completed, url, item):
    purchase_options_el = item.find(class_="s-item__purchase-options")

    # If there are no purchase options, assume auction, calculate time left
    if purchase_options_el is None:
        time_left_el = item.find(class_="s-item__time-left")
        if time_left_el is None:
            print(f"Warning: Couldn't find time on '{url}'", file=sys.stderr)
            return None
        else:
            time_left_raw = time_left_el.getText()
            time_left = re.match(r"(([0-9]+)d)? ?(([0-9]+)h)? ?(([0-9]+)m)?", time_left_raw)
            if time_left is None:
                print(f"Warning: Couldn't parse time from '{time_left_raw}' on '{url}'", file=sys.stderr)
                return None
            else:
                (_, dd_raw, _, hh_raw, _, mm_raw) = time_left.groups()
                dd = int(dd_raw) if dd_raw is not None else 0
                hh = int(hh_raw) if hh_raw is not None else 0
                mm = int(mm_raw) if mm_raw is not None else 0
                ends_at = datetime.now() + relativedelta(days=dd, hours=hh, minutes=mm)
                ends_at = ends_at.replace(microsecond=0)
                return ends_at.isoformat()

    purchase_options = purchase_options_el.getText()
    if purchase_options == 'or Best Offer':
        return 'best_offer'
    elif purchase_options == 'Buy It Now':
        return 'buy_it_now'
    else:
        print(f"Warning: Unrecognized purchase type '{purchase_options}' on '{url}'", file=sys.stderr)
        return None

def extract_product(phrase, completed, item):
    # Extract title, url, id
    title = item.find(class_="s-item__title").getText()
    url = item.find(class_="s-item__link").attrs['href'].split('?')[0]
    item_id = item.attrs['id']
    if completed:
        purchase_type = None
    else:
        purchase_type = extract_purchase_type(phrase, completed, url, item)

    return {
        'title': title,
        'id': item_id,
        'url': url,
        'purchase_type': purchase_type,
        'completed': completed
    }

def search_products(phrase, completed=False):
    soup = search(phrase, completed)
    if soup == None:
        return None
    products = {}
    for item in get_exact_items(soup):
        product = extract_product(phrase, completed, item)
        products[product['id']] = product
    return products

def update_records():
    # Load records
    records = {}
    with open("/home/dylan/ebay.json", "r") as f:
        records = json.load(f)

    # For each group, make the queries and aggregate them
    for group_name, group in records.items():
        for query in group['queries']:
            for completed in [True, False]:
                print(f"Query, completed={completed}: {query}")
                found_products = search_products(query, completed)
                if found_products == None:
                    print("Query failed!")
                else:
                    for product_id, product in found_products.items():
                        if product_id not in group['products']:
                            print(f"Found new product: {product['title']}")
                            product['seen'] = False
                            product['interesting'] = False
                            group['products'][product_id] = product
                        else:
                            group['products'][product_id].update(product)
                        group['products'][product_id]["last_retrieved"] = datetime.now().replace(microsecond=0).isoformat()
                        group['products'][product_id]["completed"] = completed

    with open("/home/dylan/ebay.json", "w") as f:
        json.dump(records, f, indent=2)

if __name__ == "__main__":
    update_records()
