from urllib.request import urlopen, Request
from json import loads, load
from tabulate import tabulate
from datetime import datetime


class Config:
    settings = load(open("settings.json"))


def make_request(url):
    header = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.146 Safari/537.36'
    }
    to_return = {}
    try:
        req = Request(url, headers=header)
        to_return['response'] = urlopen(req).read().decode()
    except Exception:
        raise
    return to_return


def main():
    response = loads(make_request(f"https://www.binance.com/bapi/earn/v2/friendly/pos/union?pageSize={Config.settings['page_size']}&pageIndex=1&status=ALL")['response'])
    head = ['COIN', 'GIORNI', 'MINIMO', 'MASSIMO', 'DISPONIBILITA', 'DATA FINE', 'APY', 'APR PRODUCT']
    prod_list = []
    for t in response['data']:
        if t['asset'] in Config.settings['tokens']:
            for p in t['projects']:
                if not p['sellOut']:
                    coin_res = float(p['upLimit']) - float(p['purchased'])
                    gain_year = f"{round(float(p['config']['annualInterestRate']) * 100, 2)} %"
                    gain_product = f"{round(float(p['config']['dailyInterestRate']) * int(p['duration']) * 100, 2)} %"
                    end = datetime.fromtimestamp(int(p['endTime']) / 1000.0).strftime('%Y-%m-%d')
                    prod_list.append([t['asset'], p['duration'], p['config']['minPurchaseAmount'], p['config']['maxPurchaseAmountPerUser'], coin_res, end, gain_year, gain_product])
    print(tabulate(prod_list, headers=head, tablefmt='orgtbl', floatfmt=".4f"))


if __name__ == '__main__':
    main()
