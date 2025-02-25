import polars as pl

class OrderBook:
    def __init__(self, n_levels: int):
        """
        Initializes an order book with n price levels.

        Parameters:
            n_levels (int): Max levels for both bid and ask sides.
        """
        self.n_levels = n_levels
        self.bids = pl.DataFrame({"bid": [], "size_bid": []}).cast({"bid": pl.Float64, "size_bid": pl.Float64})
        self.asks = pl.DataFrame({"ask": [], "size_ask": []}).cast({"ask": pl.Float64, "size_ask": pl.Float64})

    def update_order(self, price: float, size: float, side: str):
        """
        Updates the order book with a new or modified order.

        Parameters:
            price (float): Price level of the order.
            size (float): Size (quantity) of the order.
            side (str): "bid" or "ask".
        """
        price = float(price)
        size = float(size)

        if side == "bid":
            self.bids = self.bids.filter(self.bids["bid"] != price)  # Remove old bid at the same price
            if size > 0:
                new_order = pl.DataFrame({"bid": [price], "size_bid": [size]}).cast({"bid": pl.Float64, "size_bid": pl.Float64})
                self.bids = pl.concat([self.bids, new_order], how="vertical").sort("bid", descending=True).head(self.n_levels)

        elif side == "ask":
            self.asks = self.asks.filter(self.asks["ask"] != price)  # Remove old ask at the same price
            if size > 0:
                new_order = pl.DataFrame({"ask": [price], "size_ask": [size]}).cast({"ask": pl.Float64, "size_ask": pl.Float64})
                self.asks = pl.concat([self.asks, new_order], how="vertical").sort("ask").head(self.n_levels)

    def get_best_bid(self):
        """Returns the best bid price and size."""
        return (self.bids["bid"][0], self.bids["size_bid"][0]) if len(self.bids) else (None, None)

    def get_best_ask(self):
        """Returns the best ask price and size."""
        return (self.asks["ask"][0], self.asks["size_ask"][0]) if len(self.asks) else (None, None)

    def get_order_book(self):
        """Returns the full order book as a Polars DataFrame with the correct column order."""
        # Add index columns for joining
        asks_indexed = self.asks.with_columns(pl.Series("index", range(len(self.asks))))
        bids_indexed = self.bids.with_columns(pl.Series("index", range(len(self.bids))))

        # Join on index to align rows
        order_book = asks_indexed.join(bids_indexed, on="index", how="outer").drop("index")

        # Ensure correct column order & type handling
        return order_book.with_columns([
            pl.col("size_ask").cast(pl.Float64),
            pl.col("ask").cast(pl.Float64),
            pl.col("bid").cast(pl.Float64),
            pl.col("size_bid").cast(pl.Float64)
        ]).drop('index_right')


