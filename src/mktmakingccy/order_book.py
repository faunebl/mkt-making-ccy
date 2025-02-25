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

    def update_order(self, price: float, usd_size: float, side: str):
        """
        Updates an order in the order book.

        Parameters:
            price (float): Price level of the order.
            size (float): Size (quantity) of the order.
            side (str): Either "bid" or "ask".
        """

        if side == "bid":
            if usd_size > 0:
                self.bids[price] = usd_size
            elif price in self.bids:
                del self.bids[price]  # Remove order if size is zero
        elif side == "ask":
            if usd_size > 0:
                self.asks[price] = usd_size
            elif price in self.asks:
                del self.asks[price]  # Remove order if size is zero
        else:
            raise Exception(
                "Unknown value for the order side. Please use only 'bid' or 'ask'"
            )

        # Trim excess levels
        self._trim_order_book(side)

    def _trim_order_book(self, side: str):
        """
        Keeps only the top n levels in the order book.

        Parameters:
            side (str): Either "bid" or "ask".
        """

        self.bids = self.bids if side == "bid" else self.asks
        if side == "bid":
            sorted_prices = sorted(
                self.bids.keys(), reverse=True
            )  # Descending for bids
            if len(sorted_prices) > self.n_levels:
                for price in sorted_prices[self.n_levels :]:
                    del self.bids[price]  # Remove excess levels
        elif side == "ask":
            sorted_prices = sorted(self.asks.keys())  # Ascending for asks
            if len(sorted_prices) > self.n_levels:
                for price in sorted_prices[self.n_levels :]:
                    del self.asks[price]  # Remove excess levels
        else:
            raise Exception(
                "Unknown value for the order side. Please use only 'bid' or 'ask'"
            )

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
        asks_sorted = sorted(self.asks.items(), key=lambda x: x[0])  # Ascending order
        return {"bids": bids_sorted, "asks": asks_sorted}
