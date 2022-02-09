from urllib.request import urlopen, Request
from json import loads, load
from hmac import new
from hashlib import sha256
from logging import basicConfig, INFO, exception, info
from threading import Thread
from time import sleep


class MyThread (Thread):

    def __init__(self, url, exchange):
        Thread.__init__(self)
        self.url = url
        self.exchange = exchange
        self.price = 0

    def run(self):
        if self.exchange == "binance":
            self.price = float(loads(make_request(self.url)['response'])['price'])
        else:
            self.price = float(loads(make_request(self.url)['response'])['result'][0]['last_price'])


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


def main():
    basicConfig(
        filename="check.log",
        format="%(asctime)s|%(message)s",
        level=INFO)
    Config()
    old_price_binance = 0
    old_price_bybit = 0
    diff_binance = 0
    diff_bybit = 0
    thread_struct = {
        "binance": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "bybit": "https://api.bybit.com/v2/public/tickers?symbol=BTCUSD"
    }
    info("BINANCE PREZZO - DIFF - BYBIT PREZZO - DIFF - SPREAD - ABS VALUE DIFF")
    while True:
        threads = []
        for key, value in thread_struct.items():
            thread = MyThread(value, key)
            thread.setDaemon(True)
            threads.append(thread)
            thread.start()
        for t in threads:
            t.join()
        if old_price_binance != 0:
            diff_binance = round(threads[0].price - old_price_binance, 2)
        old_price_binance = threads[0].price
        if old_price_bybit != 0:
            diff_bybit = threads[1].price - old_price_bybit
        old_price_bybit = threads[1].price
        info(f'{threads[0].price} {diff_binance} {threads[1].price} {diff_bybit} | {round(threads[0].price - threads[1].price, 2)} | {round(abs(diff_binance) - abs(diff_bybit), 2)}')
        sleep(0.7)


if __name__ == "__main__":
    main()
