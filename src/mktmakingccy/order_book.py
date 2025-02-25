

class OrderBook:
    def __init__(self, n_levels: int):
        """
        Initializes an order book with n price levels.

        Parameters:
            n_levels (int): Number of price levels to maintain on both bid and ask sides.
        """
        self.n_levels = n_levels
        self.bids = {}  # Dictionary to store bid prices and sizes {price: size}
        self.asks = {}  # Dictionary to store ask prices and sizes {price: size}

    def update_order(self, price: float, size: float, side: str):
        """
        Updates an order in the order book.

        Parameters:
            price (float): Price level of the order.
            size (float): Size (quantity) of the order.
            side (str): Either "bid" or "ask".
        """
        book = self.bids if side == "bid" else self.asks

        if size > 0:
            book[price] = size
        elif price in book:
            del book[price]  # Remove order if size is zero

        # Trim excess levels
        self._trim_order_book(side)

    def _trim_order_book(self, side: str):
        """
        Keeps only the top n levels in the order book.

        Parameters:
            side (str): Either "bid" or "ask".
        """
        book = self.bids if side == "bid" else self.asks
        sorted_prices = sorted(book.keys(), reverse=(side == "bid"))  # Descending for bids, ascending for asks

        if len(sorted_prices) > self.n_levels:
            for price in sorted_prices[self.n_levels:]:
                del book[price]  # Remove excess levels

    def get_best_bid(self):
        """Returns the best bid price and size."""
        if not self.bids:
            return None, None
        best_price = max(self.bids.keys())
        return best_price, self.bids[best_price]

    def get_best_ask(self):
        """Returns the best ask price and size."""
        if not self.asks:
            return None, None
        best_price = min(self.asks.keys())
        return best_price, self.asks[best_price]

    def get_order_book(self):
        """Returns the current order book as a sorted list of bid and ask levels."""
        bids_sorted = sorted(self.bids.items(), key=lambda x: -x[0])  # Descending order
        asks_sorted = sorted(self.asks.items(), key=lambda x: x[0])   # Ascending order
        return {'bids': bids_sorted, 'asks': asks_sorted}

# # Example Usage
# order_book = OrderBook(n_levels=5)
# order_book.update_order(price=100.5, size=10, side="bid")
# order_book.update_order(price=101.0, size=15, side="bid")
# order_book.update_order(price=102.0, size=5, side="ask")
# order_book.update_order(price=102.5, size=20, side="ask")

# print("Best Bid:", order_book.get_best_bid())  # (101.0, 15)
# print("Best Ask:", order_book.get_best_ask())  # (102.0, 5)
# print("Order Book:", order_book.get_order_book())
