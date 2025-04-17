from order_book import OrderBook
from datetime import datetime
from typing import Literal, List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class TradeHistory:
    trades: List[Dict[str, Any]] = field(default_factory=list)

    def log(self, side: str, price: float, size: float, client: bool):
        self.trades.append({
            "timestamp": datetime.now(),
            "side": side,
            "price": price,
            "size": size,
            "client": client
        })

history = TradeHistory()

class Trade:
    def __init__(self, size: float, side: Literal['buy', 'sell']):
        self.size = size
        if side.strip().lower() == "buy" or side.strip().lower() == "sell":
            self.side = side.strip().lower()
        else:
            raise Exception("The side argument should be either 'buy' or 'sell'. \nPlease input a valid argument")

    def update_orderbook_with_trade(self, orderbook: OrderBook):
        if self.side == "buy":
            # making sure the trade isnt bigger than the whole order book
            max_size = orderbook.asks.select('size_ask').sum().to_series().to_list()[0]

            if self.size > max_size:
                raise Exception(f'Size is bigger than what is available in the order book. Please input a size inferior to {max_size}')
            
            best_price, best_size, _, client = orderbook.get_best_ask() # you buy at the ask and sell at the bid

            if self.size <= best_size:
                orderbook.update_order(
                    price = best_price, 
                    size = best_size - self.size, 
                    side = 'ask',
                    client = client)
            else:
                orderbook.delete_order(price=best_price, size=best_size, side='ask') #delete best order
                self.size -= best_size #updating the size
                orderbook = self.update_orderbook_with_trade(orderbook) #calling the function recursively

        elif self.side == "sell": # same thing but with bid
            max_size = orderbook.bids.select('size_bid').sum().to_series().to_list()[0]

            if self.size > max_size:
                raise Exception(f'Size is bigger than what is available in the order book. Please input a size inferior to {max_size}')
            
            best_price, best_size, _, client = orderbook.get_best_bid()

            if self.size <= best_size:
                orderbook.update_order(
                    price = best_price, 
                    size = best_size - self.size, 
                    side = 'bid',
                    client= client) #timestamp updates automatically
            else:
                orderbook.delete_order(price=best_price, size=best_size, side='bid')
                self.size -= best_size
                orderbook = self.update_orderbook_with_trade()

        #adding to trade history
        history.log(side=self.side, price=best_price, size=self.size, client=client)

        return orderbook
    
class MarketOrder:
    def __init__(self, size: float, side: Literal['bid', 'ask']):
        self.size = size
        if side.strip().lower() == "ask" or side.strip().lower() == "bid":
            self.side = side.strip().lower()
        else:
            raise Exception("The side argument should be either 'ask' or 'bid'. \nPlease input a valid argument")
    def post_market_order(self, orderbook: OrderBook, price: float = None):
        if self.side == "bid":

            best_price, best_size, _, client = orderbook.get_best_ask() # you buy at the ask and sell at the bid

            if (best_price is None) and (best_size is None): #there are no asks in the order book
                if price is None:
                    raise Exception("price argument cannot be None if there are no matching orders in the order book. Please provide a price.")
                print(f"We have reached the end of the order book. Posting order of size {self.size}")
                orderbook.update_order(
                    price=price,
                    size=self.size,
                    side='bid',
                    client = True
                ) # we post a new bid 
                #no trade to log here until that order is lifted 

            if self.size <= best_size:
                    orderbook.update_order(
                        price = best_price, 
                        size = best_size - self.size, 
                        side = 'ask',
                        client = client)
                    #logging the trade
                    history.log(side='buy', price=best_price, size=best_size, client=client)
            elif self.size > best_size:
                orderbook.delete_order(price=best_price, size=best_size, side='ask') #delete best order
                history.log(side='buy', price=best_price, size=best_size, client=client) #logging the trade
                self.size -= best_size #updating the size
                orderbook = self.post_market_order(orderbook, best_price) #calling the function recursively

        elif self.side == "ask": # same thing but with bid
            best_price, best_size, _, client = orderbook.get_best_bid() # you buy at the ask and sell at the bid

            if (best_price is None) and (best_size is None):
                if price is None:
                    raise Exception("price argument cannot be None if there are no matching orders in the order book. Please provide a price.")
                print(f"We have reached the end of the order book. Posting order of size {self.size}")
                orderbook.update_order(
                    price=price,
                    size=self.size,
                    side='ask',
                    client=True
                ) # we post a new ask 
                #no trade to log here until that order is lifted 

            if self.size <= best_size:
                    orderbook.update_order(
                        price = best_price, 
                        size = best_size - self.size, 
                        side = 'bid',
                        client=client)
                    #logging the trade
                    history.log(side='sell', price=best_price, size=best_size, client=client)
            elif self.size > best_size:
                orderbook.delete_order(price=best_price, size=best_size, side='bid') #delete best order
                history.log(side='sell', price=best_price, size=best_size, client=client) #logging the trade
                self.size -= best_size #updating the size
                orderbook = self.post_market_order(orderbook, best_price) #calling the function recursively


        return orderbook
    
class LimitOrder(MarketOrder):
    def __init__(self, size, side):
        super().__init__(size, side)
