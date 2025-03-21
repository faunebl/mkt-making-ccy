from order_book import OrderBook

class Trade:
    def __init__(self, size: float, side: str):
        self.size = size
        if side.strip().lower() == "buy" or side.strip().lower() == "sell":
            self.side = side.strip().lower()
        else:
            raise Exception("The side argument should be either 'Buy' or 'Sell'. \nPlease input a valid argument")

    def update_orderbook_with_trade(self, orderbook: OrderBook):
        if self.side == "buy":
            # making sure the trade isnt bigger than the whole order book
            max_size = orderbook.asks.select('size_ask').sum().to_series().to_list()[0]

            if self.size > max_size:
                raise Exception(f'Size is bigger than what is available in the order book. Please input a size inferior to {max_size}')
            
            best_price, best_size = orderbook.get_best_ask() # you buy at the ask and sell at the bid

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
            
            best_price, best_size = orderbook.get_best_bid()

            if self.size <= best_size:
                orderbook.update_order(
                    price = best_price, 
                    size = best_size - self.size, 
                    side = 'bid')
            else:
                orderbook.delete_order(price=best_price, size=best_size, side='bid')
                self.size -= best_size
                orderbook = self.update_orderbook_with_trade()

        return orderbook