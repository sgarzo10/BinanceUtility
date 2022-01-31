from json import loads, dumps, load
from hmac import new
from datetime import datetime
from hashlib import sha256
from tabulate import tabulate
from urllib.request import urlopen, Request
from csv import writer


class Config:

    settings = {}

    def __init__(self):
        f = open("settings.json")
        Config.settings = load(f)
        f.close()


def make_request(url, api_binance=False, body=None):
    # info("MAKE REQUEST: %s", url)
    header = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.146 Safari/537.36'
    }
    if body is not None:
        header['Content-Type'] = 'application/json'
    if api_binance:
        header['X-MBX-APIKEY'] = Config.settings['binance']['binance_info']['key']
    to_return = {}
    try:
        if body is not None:
            to_return['response'] = urlopen(Request(url, data=bytes(dumps(body), encoding="utf-8"), headers=header)).read()
        else:
            to_return['response'] = urlopen(Request(url, headers=header)).read()
        to_return['state'] = True
    except Exception as e:
        print(str(e))
        to_return['state'] = False
        to_return['response'] = "ERRORE: " + str(e)
    return to_return


def generate_signature(query_string):
    return new(bytes(Config.settings['binance']['binance_info']['secret'], 'latin-1'), msg=bytes(query_string, 'latin-1'), digestmod=sha256).hexdigest().upper()


def get_server_time():
    return loads(make_request("https://api.binance.com/api/v3/time", api_binance=True)['response'])['serverTime']


def get_spot_balance():
    to_ret = {}
    params = "timestamp=" + str(get_server_time())
    resp = make_request("https://api.binance.com/api/v3/account?" + params + "&signature=" + generate_signature(params), api_binance=True)
    spot = loads(resp['response'])
    spot_list = []
    for coin in spot["balances"]:
        if coin["asset"] in Config.settings['binance']['spot']:
            free = float(coin["free"])
            locked = float(coin["locked"])
            total = free + locked
            if total > 0:
                free = round(float(coin["free"]) / total * 100, 2)
                locked = round(float(coin["locked"]) / total * 100, 2)
            spot_list.append([coin["asset"], f'{free}%', f'{locked}%'])
            to_ret[coin["asset"]] = total
    head = ['ASSET', 'DISPONIBILI', 'IN ORDINE']
    f = open("binance/order-wallet.txt", "a")
    f.write("\n------------ WALLET SPOT ------------\n\n")
    f.write(tabulate(spot_list, headers=head, tablefmt='orgtbl', floatfmt=".2f") + "\n")
    f.close()
    return to_ret


def get_open_orders(balance):
    order_list = []
    s_price = ""
    for key, value in Config.settings['binance']['symbols'].items():
        query_string = "symbol=" + key
        resp = make_request("https://api.binance.com/api/v3/ticker/price?" + query_string, api_binance=True)
        price = loads(resp['response'])
        s_price += f'{key}: {price["price"]} {value["buy"]}\n'
        query_string = "timestamp=" + str(get_server_time()) + "&symbol=" + key
        resp = make_request("https://api.binance.com/api/v3/openOrders?" + query_string + "&signature=" + generate_signature(query_string), api_binance=True)
        orders = loads(resp['response'])
        for order in orders:
            if order['side'] == 'BUY':
                perc = round(float(order['price']) * float(order['origQty']) / balance[value['buy']] * 100, 2)
                perc_s = value["buy"]
                var_p = - (100 - round(float(order['price']) / float(price["price"]) * 100, 2))
            else:
                perc = round(float(order['origQty']) / balance[value['sell']] * 100, 2)
                perc_s = value["sell"]
                var_p = round(float(order['price']) / float(price["price"]) * 100, 2)
            order_list.append([order['symbol'], order['side'], f'{order["price"]} {value["buy"]}', f'{perc}% {perc_s}', f'{var_p}%'])
    f = open("binance/order-wallet.txt", "a")
    f.write("\n------------ PREZZO ATTUALE ------------\n\n")
    f.write(s_price)
    f.write("\n------------ ORDINI APERTI ------------\n\n")
    f.write(tabulate(order_list, headers=['ASSET', 'TIPO', 'PREZZO', 'TOTALE', 'PREZZO VAR'], tablefmt='orgtbl', floatfmt=".8f") + "\n")
    f.close()


def get_order_history():
    order_list = []
    for key, value in Config.settings['binance']['symbols'].items():
        params = "timestamp=" + str(get_server_time()) + "&symbol=" + key
        resp = make_request("https://api.binance.com/api/v3/myTrades?" + params + "&signature=" + generate_signature(params), api_binance=True)
        orders = {}
        if resp['state'] is True:
            orders = loads(resp['response'])
        c = 0
        orders.sort(key=lambda l: l['time'], reverse=True)
        for order in orders:
            if c == 7:
                break
            type_order = "SELL"
            if order['isBuyer']:
                type_order = "BUY"
            order_list.append([order['symbol'], type_order, f'{order["price"]} {value["buy"]}', (datetime.fromtimestamp(order['time']/1000.0)).strftime('%d-%m-%Y %H:%M')])
            c += 1
    head = ['ASSET', 'TIPO', 'PREZZO', 'DATA']
    f = open("binance/order-wallet.txt", "a")
    f.write("\n------------ STORICO ORDINI ------------\n\n")
    f.write(tabulate(order_list, headers=head, tablefmt='orgtbl', floatfmt=".8f") + "\n")
    f.close()
    order_list.insert(0, head)
    file = open('binance/assets.csv', 'w', newline='')
    writer(file).writerows(order_list)
    file.close()


def main():
    Config()
    f = open("binance/order-wallet.txt", "w")
    f.write("")
    f.close()
    balance = get_spot_balance()
    get_open_orders(balance)
    get_order_history()


if __name__ == '__main__':
    main()
