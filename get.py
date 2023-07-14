import bs4
import requests
import urllib.parse
import json
import datetime
import time

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

def extract_product(item):
    end = time.strptime(item.find(class_="s-item__time-end").getText(), '(%a, %H:%M)')
    curr = time.localtime()

    # sync all parts except day of week and time of day
    end.tm_year = curr.tm_year
    end.tm_mon = curr.tm_mon
    end.tm_mday = curr.tm_mday
    end.tm_yday = curr.tm_yday
    end.tm_isdst = curr.tm_isdst
    end.tm_zone = curr.tm_zone
    end.tm_gmtoff = curr.tm_gmtoff

    return {
        'title': item.find(class_="s-item__title").getText(),
        'id': item.attrs['id'],
        'seen': False,
        'interesting': False,
        'url': item.find(class_="s-item__link").attrs['href'].split('?')[0]
    }

def search_products(phrase, completed=False):
    soup = search(phrase, completed)
    if soup == None:
        return None
    products = {}
    for item in get_exact_items(soup):
        product = extract_product(item)
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
                            group['products'][product_id] = product
                        group['products'][product_id]["last_retrieved"] = str(datetime.datetime.now())
                        group['products'][product_id]["completed"] = completed

    with open("/home/dylan/ebay.json", "w") as f:
        json.dump(records, f, indent=2)

if __name__ == "__main__":
    update_records()
