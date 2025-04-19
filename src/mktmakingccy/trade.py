from order_book import OrderBook
from datetime import datetime
from typing import Literal, List, Dict, Any
from dataclasses import dataclass, field
import utils

#TODO: check if client = True is well implemented 
#TODO: FX PNL: with history: if inventory from yesterday + FX went from 1 to 2, now PNL is divided by 2 etc (PNL is expressed in $)
# rediviser partie existante du track PNL par le FX du jour (diviser par fair price de xyz)
#TODO: rebalancing de l'order book (refill qd trade et reset à la fin de chaque journée -> recupérer le dataframe du bid ask de tt les jour)
# masque pour récupérer juste la premiere heure de la journée
# faire tourner la fonction 15 fois car prix différent pour chaque niveau 
# réutiliser la fonction et appliqué le masque sur la 2e h de la journée plutot que juste la 1ere 
# petite fonction de raph : génère que 1 seul prix (avec taille du trade etc)

@dataclass
class TradeHistory:
    trades: List[Dict[str, Any]] = field(default_factory=list)
    _template: Dict[str, Any] = field(
        default_factory=lambda: {
            "timestamp":None,
            "side": None,
            "price": None,
            "size": None,
            "client":None,
        },
        init=False,
        repr=False
    )

    def log(self, side: str, price: float, size: float, client: bool):
        entry = self._template.copy()
        entry.update({
            "timestamp": datetime.now(),
            "side":side,
            "price":price,
            "size": size,
            "client": client,
        })
        self.trades.append(entry)


history = TradeHistory()


class Trade:
    def __init__(self, size: float, side: Literal["buy", "sell"]):
        self.size = size
        if side.strip().lower() == "buy" or side.strip().lower() == "sell":
            self.side = side.strip().lower()
        else:
            raise Exception(
                "The side argument should be either 'buy' or 'sell'. \nPlease input a valid argument"
            )

    def update_orderbook_with_trade(self, orderbook: OrderBook, fair_price: float, trade_date: datetime = None): #TODO ajouter datetime?? enlever timestamp de l'orderbook??
        if self.side == "buy":
            # making sure the trade isnt bigger than the whole order book
            max_size = orderbook.asks.select("size_ask").sum().to_series().to_list()[0]

            if self.size > max_size:
                raise Exception(
                    f"Size is bigger than what is available in the order book. Please input a size inferior to {max_size}"
                )

            best_price, best_size, _, client = (
                orderbook.get_best_ask()
            )  # you buy at the ask and sell at the bid

            if self.size <= best_size:
                orderbook.update_order(
                    price=best_price,
                    size=best_size - self.size,
                    side="ask",
                    client=client,
                )
                if not client:
                    new_ask = utils.compute_one_new_ask(fair_price=fair_price, old_ask=best_price, size=self.size) #TODO récupérer le fair price
                    orderbook.update_order(
                        price=new_ask,
                        size= self.size,
                        side='ask',
                        client=False
                    )
            else:
                orderbook.delete_order(
                    price=best_price, size=best_size, side="ask"
                )  # delete best order
                if not client:
                    new_ask = utils.compute_one_new_ask(fair_price=fair_price, old_ask=best_price, size=best_size) #TODO récupérer le fair price
                    orderbook.update_order(
                        price=new_ask,
                        size= best_size,
                        side='ask',
                        client=False
                    )
                self.size -= best_size  # updating the size
                orderbook = self.update_orderbook_with_trade(
                    orderbook
                )  # calling the function recursively

        elif self.side == "sell":  # same thing but with bid
            max_size = orderbook.bids.select("size_bid").sum().to_series().to_list()[0]

            if self.size > max_size:
                raise Exception(
                    f"Size is bigger than what is available in the order book. Please input a size inferior to {max_size}"
                )

            best_price, best_size, _, client = orderbook.get_best_bid()

            if self.size <= best_size:
                orderbook.update_order(
                    price=best_price,
                    size=best_size - self.size,
                    side="bid",
                    client=client,
                )  # timestamp updates automatically
                if not client:
                    new_bid = utils.compute_one_new_bid(fair_price=fair_price, old_ask=best_price, size=self.size) #TODO récupérer le fair price
                    orderbook.update_order(
                        price=new_bid,
                        size= self.size,
                        side='bid',
                        client=False
                    )
            else:
                orderbook.delete_order(price=best_price, size=best_size, side="bid")
                if not client:
                    new_bid = utils.compute_one_new_bid(fair_price=fair_price, old_ask=best_price, size=best_size) #TODO récupérer le fair price
                    orderbook.update_order(
                        price=new_bid,
                        size= best_size,
                        side='bid',
                        client=False
                    )
                self.size -= best_size
                orderbook = self.update_orderbook_with_trade()

        # adding to trade history
        history.log(side=self.side, price=best_price, size=self.size, client=client)

        return orderbook


class MarketOrder:
    def __init__(self, size: float, side: Literal["bid", "ask"]):
        self.size = size
        if side.strip().lower() == "ask" or side.strip().lower() == "bid":
            self.side = side.strip().lower()
        else:
            raise Exception(
                "The side argument should be either 'ask' or 'bid'. \nPlease input a valid argument"
            )

    def post_market_order(self, orderbook: OrderBook, price: float = None):
        if self.side == "bid":
            best_price, best_size, _, client = (
                orderbook.get_best_ask()
            )  # you buy at the ask and sell at the bid

            if (best_price is None) and (
                best_size is None
            ):  # there are no asks in the order book
                if price is None:
                    raise Exception(
                        "price argument cannot be None if there are no matching orders in the order book. Please provide a price."
                    )
                print(
                    f"We have reached the end of the order book. Posting order of size {self.size}"
                )
                orderbook.update_order(
                    price=price, size=self.size, side="bid", client=True
                )  # we post a new bid
                # no trade to log here until that order is lifted

            if self.size <= best_size:
                orderbook.update_order(
                    price=best_price,
                    size=best_size - self.size,
                    side="ask",
                    client=client,
                )
                # logging the trade
                history.log(side="buy", price=best_price, size=best_size, client=client)
            elif self.size > best_size:
                orderbook.delete_order(
                    price=best_price, size=best_size, side="ask"
                )  # delete best order
                history.log(
                    side="buy", price=best_price, size=best_size, client=client
                )  # logging the trade
                self.size -= best_size  # updating the size
                orderbook = self.post_market_order(
                    orderbook, best_price
                )  # calling the function recursively

        elif self.side == "ask":  # same thing but with bid
            best_price, best_size, _, client = (
                orderbook.get_best_bid()
            )  # you buy at the ask and sell at the bid

            if (best_price is None) and (best_size is None):
                if price is None:
                    raise Exception(
                        "price argument cannot be None if there are no matching orders in the order book. Please provide a price."
                    )
                print(
                    f"We have reached the end of the order book. Posting order of size {self.size}"
                )
                orderbook.update_order(
                    price=price, size=self.size, side="ask", client=True
                )  # we post a new ask
                # no trade to log here until that order is lifted

            if self.size <= best_size:
                orderbook.update_order(
                    price=best_price,
                    size=best_size - self.size,
                    side="bid",
                    client=client,
                )
                # logging the trade
                history.log(
                    side="sell", price=best_price, size=best_size, client=client
                )
            elif self.size > best_size:
                orderbook.delete_order(
                    price=best_price, size=best_size, side="bid"
                )  # delete best order
                history.log(
                    side="sell", price=best_price, size=best_size, client=client
                )  # logging the trade
                self.size -= best_size  # updating the size
                orderbook = self.post_market_order(
                    orderbook, best_price
                )  # calling the function recursively

        return orderbook


class LimitOrder(MarketOrder):
    def __init__(self, size, side):
        super().__init__(size, side)
        #TODO
