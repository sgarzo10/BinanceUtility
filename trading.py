from urllib.request import urlopen, Request
from logging import info, exception, basicConfig, INFO
from json import loads, load
from hmac import new
from hashlib import sha256
from argparse import ArgumentParser
from sys import exit, argv


class Config:
    settings = load(open("settings.json"))


def make_request(url, body=None, method=None):
    info("MAKE REQUEST: %s", url)
    if body is not None:
        info("BODY: %s", body.decode())
    header = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.146 Safari/537.36',
        'X-MBX-APIKEY': Config.settings['binance_info']['key']
    }
    to_return = {}
    try:
        if body is not None and method is not None:
            req = Request(url, headers=header, data=body, method=method)
        else:
            if body is not None:
                req = Request(url, headers=header, data=body)
            else:
                req = Request(url, headers=header)
        to_return['response'] = urlopen(req).read().decode()
        info("RESPONSE: %s", to_return['response'])
    except Exception:
        raise
    return to_return


def generate_signature(query_string):
    return new(bytes(Config.settings['binance_info']['secret'], 'latin-1'), msg=bytes(query_string, 'latin-1'), digestmod=sha256).hexdigest().upper()


def get_server_time():
    return loads(make_request("https://api.binance.com/api/v3/time")['response'])['serverTime']


def find_order(typology, symbol, price, quantity):
    to_ret = {
        'order_open': False,
        'order_id': 0
    }
    query_string = "timestamp=" + str(get_server_time())
    resp = make_request("https://api.binance.com/api/v3/openOrders?" + query_string + "&signature=" + generate_signature(query_string))
    orders = loads(resp['response'])
    for order in orders:
        if order['side'] == typology and order['symbol'] == symbol and float(order['price']) == float(price) and float(order['origQty']) == float(quantity):
            to_ret['order_id'] = order['orderId']
            to_ret['order_open'] = True
            break
    return to_ret


def do_action(operation, typology, symbol, price, quantity):
    try:
        Config()
        if operation == 'check':
            if find_order(typology, symbol, price, quantity)['order_open']:
                info("ORDER FOUND")
                exit(1)
            else:
                info("ORDER NOT FOUND")
                exit(0)
        if operation == 'insert':
            query_string = "symbol=" + symbol + "&side=" + typology + "&type=LIMIT&timeInForce=GTC&quantity=" + quantity + "&price=" + price + "&timestamp=" + str(get_server_time())
            query_string += "&signature=" + generate_signature(query_string)
            make_request("https://api.binance.com/api/v3/order", body=str.encode(query_string))
            info("INSERT ORDER: %s %s %s %s", typology, symbol, quantity, price)
            exit(1)
        if operation == 'delete':
            order = find_order(typology, symbol, price, quantity)
            if order['order_open']:
                query_string = "symbol=" + symbol + "&orderId=" + str(order['order_id']) + "&timestamp=" + str(get_server_time())
                query_string += "&signature=" + generate_signature(query_string)
                make_request("https://api.binance.com/api/v3/order", body=str.encode(query_string), method="DELETE")
                info("DELETE ORDER: %s %s %s %s", typology, symbol, quantity, price)
                exit(1)
            else:
                info("ANY ORDER FOUND TO DELETE")
                exit(0)
    except Exception as e:
        exception(e)
        exit(10)


if __name__ == '__main__':
    basicConfig(
        filename="order.log",
        format="%(asctime)s|%(levelname)s|%(filename)s:%(lineno)s|%(message)s",
        level=INFO)
    p = ArgumentParser()
    p.add_argument("-o", "--operation", help="Set operation: 'check', 'insert', 'delete'", type=str)
    p.add_argument("-t", "--typology", help="Set type of operation: 'BUY', 'SELL'", type=str)
    p.add_argument("-s", "--symbol", help="Set symbol of operation, es. BTCBUSD", type=str)
    p.add_argument("-p", "--price", help="Set price of operation: es. 35000.34", type=str)
    p.add_argument("-q", "--quantity", help="Set quantity of operation: es. 0.01", type=str)
    opt = p.parse_args()
    if len(argv) < 11:
        p.print_help()
        exit(10)
    else:
        info("-------------------------------------------- NEW RUN --------------------------------------------")
        info("PARAMETER: %s %s %s %s %s", opt.operation, opt.typology, opt.symbol, opt.price, opt.quantity)
    do_action(opt.operation, opt.typology, opt.symbol, opt.price, opt.quantity)
