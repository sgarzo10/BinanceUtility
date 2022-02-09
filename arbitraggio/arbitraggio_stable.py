from urllib.request import urlopen, Request
from json import loads, load
from hmac import new
from hashlib import sha256
from time import sleep
from logging import basicConfig, INFO, exception, info


class Config:

    settings = {}

    def __init__(self):
        f = open("settings.json")
        Config.settings = load(f)
        f.close()


def make_request(url, api_binance=False, body=None):
    header = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.146 Safari/537.36'
    }
    timeout = 30
    if body is not None:
        header['Content-Type'] = 'application/json'
    if api_binance:
        header['X-MBX-APIKEY'] = Config.settings['binance']['binance_info']['key']
    to_return = {}
    try:
        if body is not None:
            to_return['response'] = urlopen(Request(url, data=str.encode(body), headers=header), timeout=timeout).read()
        else:
            to_return['response'] = urlopen(Request(url, headers=header), timeout=timeout).read()
        to_return['state'] = True
    except Exception as e:
        info("MAKE REQUEST: %s", url)
        exception(e)
        to_return['state'] = False
        to_return['response'] = "ERRORE: " + str(e)
    return to_return


def generate_signature(query_string):
    return new(bytes(Config.settings['binance']['binance_info']['secret'], 'latin-1'), msg=bytes(query_string, 'latin-1'), digestmod=sha256).hexdigest().upper()


def get_server_time():
    return loads(make_request("https://api.binance.com/api/v3/time", api_binance=True)['response'])['serverTime']


def get_open_orders():
    query_string = "timestamp=" + str(get_server_time()) + "&symbol=" + Config.settings['binance']['symbol']
    resp = make_request("https://api.binance.com/api/v3/openOrders?" + query_string + "&signature=" + generate_signature(query_string), api_binance=True)
    to_ret = "NA"
    price = ""
    qty = ""
    if resp['state'] is True:
        orders = loads(resp['response'])
        if len(orders) >= 1:
            to_ret = orders[0]['side']
            price = round(float(orders[0]['price']), 4)
            qty = round(float(orders[0]['origQty']), 2)
    return to_ret, price, qty


def get_order_history():
    total_sell = 0
    total_buy = 0
    total_comm = 0
    type_order = ""
    params = "timestamp=" + str(get_server_time()) + "&symbol=" + Config.settings['binance']['symbol']
    resp = make_request("https://api.binance.com/api/v3/myTrades?" + params + "&signature=" + generate_signature(params), api_binance=True)
    if resp['state'] is True:
        orders = loads(resp['response'])
        for order in orders:
            type_order = "SELL"
            total_comm += float(order['commission'])
            if order['isBuyer']:
                type_order = "BUY"
                total_buy += float(order['quoteQty'])
            else:
                total_sell += float(order['quoteQty'])
    return type_order, round(total_sell - total_buy, 2), total_comm


def main():
    basicConfig(
        filename=None,  # "bot.log",
        format="%(asctime)s|%(levelname)s|%(filename)s:%(lineno)s|%(message)s",
        level=INFO)
    Config()
    quantity = str(Config.settings['binance']['quantity'])
    count = 0
    while True:
        type_order, gain, tot_comm = get_order_history()
        order_side, price, qty = get_open_orders()
        if count == Config.settings['binance']['freq_log']:
            info("-----------------------------------------")
            info("ULTIMO ORDINE ESEGUITO %s - GAIN ATTUALE %s$ - FEE %s BNB", type_order, gain, tot_comm)
            info("ORDINE APERTO: %s %s %s", order_side, price, qty)
            count = 0
        if type_order != order_side:
            if order_side == "NA":
                info("ORDINE FILLATO")
                if type_order == "SELL":
                    typology = "BUY"
                    price = str(Config.settings['binance']['buy_price'])
                else:
                    typology = "SELL"
                    price = str(Config.settings['binance']['sell_price'])
                query_string = "symbol=" + Config.settings['binance']['symbol'] + "&side=" + typology + "&type=LIMIT&timeInForce=GTC&quantity=" + quantity + "&price=" + price + "&timestamp=" + str(get_server_time())
                query_string += "&signature=" + generate_signature(query_string)
                make_request("https://api.binance.com/api/v3/order", api_binance=True, body=query_string)
                info("INSERT ORDER: %s %s %s %s", typology, Config.settings['binance']['symbol'], price, quantity)
        sleep(Config.settings['binance']['freq_update'])
        count += 1


if __name__ == '__main__':
    main()
