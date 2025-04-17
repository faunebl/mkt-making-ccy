from order_book import OrderBook
from datetime import datetime
import polars as pl
from typing import Literal, List, Dict, Any
from dataclasses import dataclass, field

#TODO : better history management ?

@dataclass
class TradeHistory:
    trades: List[Dict[str, Any]] = field(default_factory=list)

    def log(self, side: str, price: float, size: float):
        self.trades.append({
            "timestamp": datetime.now(),
            "side": side,
            "price": price,
            "size": size,
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
            
            best_price, best_size, _ = orderbook.get_best_ask() # you buy at the ask and sell at the bid

            if self.size <= best_size:
                orderbook.update_order(
                    price = best_price, 
                    size = best_size - self.size, 
                    side = 'ask')
            else:
                orderbook.delete_order(price=best_price, size=best_size, side='ask') #delete best order
                self.size -= best_size #updating the size
                orderbook = self.update_orderbook_with_trade(orderbook) #calling the function recursively

        elif self.side == "sell": # same thing but with bid
            max_size = orderbook.bids.select('size_bid').sum().to_series().to_list()[0]

            if self.size > max_size:
                raise Exception(f'Size is bigger than what is available in the order book. Please input a size inferior to {max_size}')
            
            best_price, best_size, _ = orderbook.get_best_bid()

            if self.size <= best_size:
                orderbook.update_order(
                    price = best_price, 
                    size = best_size - self.size, 
                    side = 'bid') #timestamp updates automatically
            else:
                orderbook.delete_order(price=best_price, size=best_size, side='bid')
                self.size -= best_size
                orderbook = self.update_orderbook_with_trade()

        #adding to trade history
        history.log(side=self.side, price=best_price, size=self.size)

        return orderbook
    
class MarketOrder():
    def __init__(self, size: float, side: Literal['bid', 'ask']):
        self.size = size
        if side.strip().lower() == "ask" or side.strip().lower() == "bid":
            self.side = side.strip().lower()
        else:
            raise Exception("The side argument should be either 'ask' or 'bid'. \nPlease input a valid argument")
    def post_market_order(self, orderbook: OrderBook):
        if self.side == "bid":
            # making sure the trade isnt bigger than the whole order book
            max_size = orderbook.asks.select('size_ask').sum().to_series().to_list()[0] # this is 0 if there are no asks in the order book
            if self.size > max_size:
                remaining_size = max_size - self.size
                print(f"The order size is superior to the depth of the order book. Creating order of size {remaining_size}")
                # we get the worst possible price
                worst_price, _, _ = orderbook.asks.bottom_k(k=1, by='ask').row(index=0) #gives us the worst available ask
                #we delete all asks
                orderbook.asks.filter(pl.col('ask').is_null()) #deletes all asks
                # posting new order
                orderbook.update_order(
                    price=worst_price,
                    size=remaining_size,
                    side='bid'
                )
            else:
                best_price, best_size, _ = orderbook.get_best_ask() # you buy at the ask and sell at the bid

                if self.size <= best_size:
                        orderbook.update_order(
                            price = best_price, 
                            size = best_size - self.size, 
                            side = 'ask')
                else:
                    orderbook.delete_order(price=best_price, size=best_size, side='ask') #delete best order
                    self.size -= best_size #updating the size
                    orderbook = self.post_market_order(orderbook) #calling the function recursively

        elif self.side == "ask": # same thing but with bid
            # making sure the trade isnt bigger than the whole order book
            max_size = orderbook.asks.select('size_bid').sum().to_series().to_list()[0] # this is 0 if there are no asks in the order book
            if self.size > max_size:
                remaining_size = max_size - self.size
                print(f"The order size is superior to the depth of the order book. Creating order of size {remaining_size}")
                # we get the worst possible price
                worst_price, _, _ = orderbook.bids.bottom_k(k=1, by='bid').row(index=0) #gives us the worst available ask
                #we delete all asks
                orderbook.asks.filter(pl.col('bid').is_null()) #deletes all asks
                # posting new order
                orderbook.update_order(
                    price=worst_price,
                    size=remaining_size,
                    side='ask'
                )
            else:
                best_price, best_size, _ = orderbook.get_best_bid() # you buy at the ask and sell at the bid

                if self.size <= best_size:
                        orderbook.update_order(
                            price = best_price, 
                            size = best_size - self.size, 
                            side = 'bid')
                else:
                    orderbook.delete_order(price=best_price, size=best_size, side='ask') #delete best order
                    self.size -= best_size #updating the size
                    orderbook = self.post_market_order(orderbook) #calling the function recursively


        return orderbook