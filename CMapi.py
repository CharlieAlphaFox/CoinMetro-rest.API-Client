import requests
from typing import Any

''' All methods with the classmethod decorator are bound to the
class and can be run without creating an object(hence no auth). Example-

CMClient.get_trading_assets()

Most data heavy methods have a filterBy parameter which can be used to
filter out required data(if left empty a raw json dictionary is returned). Example-

CMClient.get_latest_prices(filterBy={"pair":"BTCEUR"})

'''

BASE="https://api.coinmetro.com"

class CMClient:
    def __init__(self, email:str, passwd:str, hashkey:str):

        self.userId = None
        self.bearerToken = None

        data = {"login":email, "password":passwd, "g-recaptcha-response":hashkey}
        headers={"Content-Type":"application/x-www-form-urlencoded","X-OTP":"","X-Device-Id":"bypass" }
        apiSession = requests.post(url=f"{BASE}/jwt",headers=headers,data=data)
        sc = apiSession.status_code

        if 199 < sc <=299:
            self.bearerToken = "Bearer "+apiSession.json()["token"]
            self.userId = apiSession.json()["userId"]

        else:
            print(apiSession.text)
            raise Exception("The client failed to initialize. Refer to the above for details.")

    '''methods start here'''
    def initiate_payment(self,amount:str, currency:str, payment_method:str="everypay", **kwgs):
        headers = {"Content-Type":"application/x-www-form-urlencoded", "Authorization":self.bearerToken}
        data = {"amount":amount, "currency":currency, "paymentMethod":payment_method}
        if kwgs.get("cardId"):
            data.update({"cardId":kwgs['cardId']})

        response = requests.post(f"{BASE}/payments",headers=headers, data=data)
        return self.json_response(response)

    def withdraw(self, amount:str, currency:str, wallet:str):
        '''
        (From the docs)
        The destiation, in the field wallet, supports the following formats:
        For EUR: {{IBAN}}:{{BIC}}
        For BTC/ETH/LTC/BCH: {{cryptoAddress}}
        For XRP and XLM: {{cryptoAddress}}:{{destinationTag}}
        Example from docs: FR9130066929721543148898291:CMCIFRPPXXX
        '''

        headers = {"Content-Type":"application/x-www-form-urlencoded","Authorization":self.bearerToken,"X-OTP":""}
        data = {"amount":amount, "currency":currency, "wallet":wallet}
        response = requests.post(f"{BASE}/withdraw",headers=headers, data=data)

        return self.json_response(response)

    def ensure_wallet(self, currency:str) -> Any:
        return self.common_json_methods(f"/users/wallets/{currency}")

    def delete_saved_address(self, addressId:str):
        response = requests.delete(f"{BASE}/withdraw/saved-addresses/{addressId}", headers={"Authorization":self.bearerToken})
        if 199 < response.status_code <= 299:
            print("successfully deleted message")
        else:
            self._request_not_successful(response)

    def get_margin_info(self) -> Any:
        return self.common_json_methods("/exchange/margin")

    def get_saved_addresses(self) -> Any:
        return self.common_json_methods("/withdraw/saved-addresses")

    def get_saved_cards(self) -> Any:
        return self.common_json_methods("/payments/saved-cards")

    def get_wallets(self) -> Any:
        return self.common_json_methods("/users/wallets")

    def get_wallet_histories(self, since:int) -> Any:
        return self.common_json_methods(f"/users/wallets/history/{since}?")

    def get_balances(self) -> Any:
        return self.common_json_methods("/users/balances")

    def get_profile(self) -> Any:
        headers={"Authorization":self.bearerToken,"Content-Type":self.bearerToken}
        response = requests.get(f"{BASE}/account/profile",headers=headers)
        return self.json_response(response)

    def get_order_status(self,orderId:str) -> Any:
        return self.common_json_methods(f"/exchange/orders/status/{orderId}")

    def get_order_history(self,since:int) -> Any:
        return self.common_json_methods(f"/exchange/orders/history/{since}")

    def get_open_orders(self) -> Any:
        return self.common_json_methods("/exchange/orders/active")

    def get_order_fills(self,since:int) -> Any:
        return self.common_json_methods(f"/exchange/fills/{since}?")

    @classmethod
    def get_full_book(self, pair:str, filterBy:dict=None) -> Any:
        response = requests.get(f"{BASE}/exchange/book/{pair}")
        res = self._common_response(self, response, sortby="book", filterBy=filterBy)
        return res

    @classmethod
    def get_book_updates(self, pair:str, From:int=0,filterBy:dict =None) -> Any:
        response = requests.get(f"{BASE}/exchange/bookUpdates/{pair}/{From}")
        if 199 < response.status_code <= 299:
            if filterBy is not None:
                res = self._search(self, response.json(), filterBy)
                if res[0]:
                    return res[1]
                return [{}]
            return response.json()
        else:
            self._request_not_successful(response)

    @classmethod
    def get_latest_trades(self, pair:str, From:int) -> Any:
        response  = requests.get(f"{BASE}/exchange/ticks/{pair}/{From}")
        if 199 < response.status_code <= 299:
            return response.json()
        else:
            self._request_not_successful(response)

    @classmethod
    def get_latest_prices(self, filterBy:dict=None) -> Any:
        response = requests.get(f"{BASE}/exchange/prices")
        resp = self._common_response(self, response=response, filterBy=filterBy,
        sortby="latestPrices")

        return resp

    @classmethod
    def get_trading_markets(self, filterBy:dict =None) -> Any:
        response = requests.get(f"{BASE}/markets")
        if 199 < response.status_code <= 299:
            if filterBy is not None:
                res = self._search(self,response.json(),filterBy)
                if res[0]:
                    return res[1]
                return [{}]

            return response.json() #returns raw json as dict if pair not specified
        else:
             self._request_not_successful(self)

    @classmethod
    def get_trading_assets(self, filterBy:dict = None) -> Any:
        response = requests.get(f"{BASE}/assets")
        if 199 < response.status_code <= 299:
            if filterBy is not None:
                res = self._search(self, response.json(), filterBy)
                if res[0]:
                    return res[1]
                return [{}]
            return response.json()
        else:
            self._request_not_successful(response)

    @classmethod
    def get_historical_prices(self, pair:str, timeframe:int, filterBy:dict = None, **kwargs) -> Any:
        FROM=""
        TO=""
        if kwargs.get("From"):
            FROM=kwargs["From"]

        if kwargs.get("To"):
            TO=kwargs["To"]

        response = requests.get(f"{BASE}/open/exchange/candles/{pair}/{timeframe}/{FROM}/{TO}")
        resp = self._common_response(self, response=response, sortby="candleHistory", filterBy=filterBy)
        return resp

    def place_buy_order(self, orderType:str, buyingCurrency:str, sellingCurrency:str, buyingQty:str, **kwgs) -> Any:
        #Market order
        '''
        (From the docs)
        One (and only one) ofbuyingQtyor sellingQty is required for market orders, both for limit orders.
        For limit orders, by default, the order is considered filled when either buyingQty or sellingQty is filled.
        Use the fillStyle property to change this behaviour.
        '''

        headers={"Authorization":self.bearerToken, 'Content-Type': 'application/x-www-form-urlencoded'}
        payload = f'orderType={orderType}&buyingCurrency={buyingCurrency}&sellingCurrency={sellingCurrency}&buyingQty={buyingQty}'

        response = requests.request("POST", f'{BASE}/exchange/orders/create', headers=headers, data = payload)

        return self.json_response(response)

    def place_sell_order(self, orderType:str, buyingCurrency:str, sellingCurrency:str, sellingQty:str, **kwgs) -> Any:
        # Market order
        '''
        (From the docs)
        One (and only one) ofbuyingQtyor sellingQty is required for market orders, both for limit orders.
        For limit orders, by default, the order is considered filled when either buyingQty or sellingQty is filled.
        Use the fillStyle property to change this behaviour.
        '''

        headers={"Authorization":self.bearerToken, 'Content-Type': 'application/x-www-form-urlencoded'}
        payload = f'orderType={orderType}&buyingCurrency={buyingCurrency}&sellingCurrency={sellingCurrency}&sellingQty={sellingQty}'

        response = requests.request("POST", f'{BASE}/exchange/orders/create', headers=headers, data = payload)

        return self.json_response(response)

    def place_limit_order(self, orderType:str, buyingCurrency:str, sellingCurrency:str, buyingQty:str, **kwgs) -> Any:
        #limit orders include margin orders, Stop Limit Orders,

        headers={"Authorization":self.bearerToken, 'Content-Type': 'application/x-www-form-urlencoded'}
        payload = f'orderType={orderType}&buyingCurrency={buyingCurrency}&sellingCurrency={sellingCurrency}&buyingQty={buyingQty}&sellingQty={sellingQty}'

        if kwgs.get("timeInForce"): # 'GTC': 1, 'IOC': 2, 'GTD': 3, 'FOK': 4
            payload+= f"&timeInForce={str(kwgs['timeInForce'])}"
        if kwgs.get("expirationTime"):
            payload+= f"&expirationTime={str(kwgs['expirationTime'])}"
        else:
            raise Exception("Time in Force needs expirationTime")
        if kwgs.get("stopPrice"):
            payload+= f"&stopPrice={str(kwgs['stopPrice'])}"
        if kwgs.get("margin"): #takes a boolean as true or false
            payload+= f"&margin={str(kwgs['margin'])}"
        if kwgs.get("fillStyle"):
            payload+= f"&fillStyle={str(kwgs['fillStyle'])}"

        response = requests.request("POST", f'{BASE}/exchange/orders/create', headers=headers, data = payload)

        return self.json_response(response)

    '''methods end here'''

    ''' utility methods start here'''
    def _request_not_successful(self, response):
        raise Exception(response)

    def _search(self, dictionary:list, filterdict:dict) -> tuple:
        results = []
        for d in dictionary:
            for key, val in filterdict.items():
                try:
                    if d[key]==val:
                        results.append(d)
                except KeyError:
                    return False, None
                continue

        if results !=[]:
            return True, results
        else:
            return False, None


    def _common_response(self, response,sortby,filterBy=None):
        if 199 < response.status_code <= 299:
            if filterBy is not None:
                res = self._search(self,response.json()[sortby],filterBy) #filters json by pair and returns the pertaining dictionary
                if res[0]:
                    return res[1]
                return [{}]

            return response.json()   #returns raw json as dict if pair not specified

        else:
            print(response.status_code, response.json())
            self._request_not_successful(response)

    def json_response(self, response):
        if 199 < response.status_code <= 299:
            return response.json()
        else:
            print(response.status_code ,response.json())
            self._request_not_successful(response)

    def common_json_methods(self,endpoint:str):
        headers={"Authorization":self.bearerToken}
        response = requests.get(f"{BASE}{endpoint}",headers=headers)
        return self.json_response(response)

    '''utility methods end here'''
