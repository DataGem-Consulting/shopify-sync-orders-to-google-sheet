import requests
import datetime
import json
import os 

class ShopifyHandler():
    def __init__(self,
                 shopifyCredentials = None,
                 defaultStartTime = (datetime.datetime.now() - datetime.timedelta(days=14)).strftime('%Y-%m-%dT%H:%M:%S%z'),
                 defaultEndTime = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z'),
                 ):
        self.defaultStartTime = defaultStartTime
        self.defaultEndTime = defaultEndTime
        self.getCredentials(shopifyCredentials)

    def getCredentials(self, shopifyCredentials):
        """ Get the credentials for the Shopify API.
        Args:
            shopifyCredentials (dict): The Shopify credentials.
        Returns:
            Credentials: The credentials for the Shopify API.
        """
        if not shopifyCredentials:
            try:
                with open('var/shopify_credentials.json', 'r') as file:
                    shopifyCredentials = json.load(file)
            except FileNotFoundError:
                shopifyCredentials = os.environ.get('SHOPIFY_CREDENTIALS', '{}')
                shopifyCredentials = json.loads(shopifyCredentials)
        # print("Using Shopify credentials:", shopifyCredentials)
        self.API_KEY = shopifyCredentials['shopify']['API_KEY']
        self.API_TOKEN = shopifyCredentials['shopify']['API_TOKEN']
        self.MERCHANT = shopifyCredentials['shopify']['MERCHANT']
        self.VERSION = shopifyCredentials['shopify'].get('VERSION', '2025-07')

    def fetchQueryData(self,object : str,param: dict) -> list[dict]:
        """
        Fetch data from Shopify API \n
        Args:
            object (str): Object to fetch
            param (dict): Parameters to use
        Returns:
            data (list): Data fetched
        """
        last = 0
        data = []
        param['limit'] = 250
        data_length = 0
        while True:
            param['since_id'] = last
            url = f"https://{self.MERCHANT}.myshopify.com/admin/api/{self.VERSION}/{object}.json"
            headers = {
                "X-Shopify-Access-Token": self.API_TOKEN,
                "Content-Type": "application/json"
            }
            response = requests.request("GET", url, headers=headers, params=param)
            try:
                new_data = response.json()[object] 
                data += new_data
                data_length += len(new_data)
                last=data[-1]['id']
                if len(new_data)<250 or param['since_id'] == last:
                    break
            except Exception as e:
                print(f"Error fetching data from Shopify: {e}")
                print(f"Response {response.status_code}: {response.json()}")
                break
        return(data)

    def getOrders(self,status = 'any',start_time = None,end_time = None) -> list[dict]:
        """
        Get Orders from Shopify API \n
        Args:
            status (str): Order status to fetch
            start_time (str): Minimum start time
            end_time (str): Maximum end time
           
        Returns:
            data (list): Orders fetched
        """
        object = 'orders'
        if start_time is None:
            start_time = self.defaultStartTime
        if end_time is None:
            end_time = self.defaultEndTime

        print(f"Fetching orders from {start_time} to {end_time} with status {status}")

        param = {"status":status,
                 "created_at_min":start_time,
                 "created_at_max":end_time}
        return self.fetchQueryData(object,param)
    
    def parse_order(self, order : dict) -> dict:
        """
        Parse a Shopify order to a simplified format.
        Args:
            order (dict): The order data from Shopify.
        Returns:
            dict: A simplified order dictionary.
        """
        
        return {
            'N° commande': str(order.get('id')),
            'Date de commande': datetime.datetime.strptime(order.get('created_at'), '%Y-%m-%dT%H:%M:%S%z').strftime("%Y-%m-%d"),
            'Total': order.get('total_price'),
            'Total produit': order.get('total_line_items_price'),
            'Promotions': order.get('total_discounts'),
            'Frais de port': order.get('total_shipping_price_set', {}).get('shop_money', {}).get('amount', '0'),
            'Taxes': order.get('total_tax'),
            'Devise': order.get('currency'),
            'Client ID': order.get('customer', {}).get('id', ''),
            'Adresse de livraison': order.get('shipping_address', {}).get('address1', '') + ', ' + order.get('shipping_address', {}).get('city', '') + ', ' + order.get('shipping_address', {}).get('country', '') if order.get('shipping_address') else '',
            'Email': order.get('email', ''),
            'Produits': '\n'.join([item['title'] +f"({item['quantity']}x{item['price']}{item['price_set']['shop_money']['currency_code']})" for item in order.get('line_items', [])])
        }