import polars as pl
from typing import Literal
from datetime import datetime

#TODO: utiliser la fct qui créer la proba de trade pour créer une fct qui génère l'instance de market order en fct de la proba 
# resultat final: colonne appelée market order ou chaque élément est une instace de market order _
# ou en fct de la proba ça va dire s'il y a eu un market order ou pas _
# avec petite proba sur les grosses tailles et grande proba sur les petites tailles 
# taille est générée de manière aléatoire (random.random()) : max d'une taille = 10M et faire le mapping avec les proba
# faire le croisement entre les différents dataframe pour générer des trades

class OrderBook:
    def __init__(self, n_levels: int) -> None:
        """
        Initializes an order book with n price levels.

        Parameters:
            n_levels (int): Max levels for both bid and ask sides.
        """
        self.n_levels = n_levels
        self.bids = pl.DataFrame(
            {"bid": [], "size_bid": [], "timestamp_bid": [], "client_bid": []}
        ).cast(
            {
                "bid": pl.Float64,
                "size_bid": pl.Float64,
                "timestamp_bid": pl.Datetime,
                "client_bid": pl.Boolean,
            }
        )
        self.asks = pl.DataFrame(
            {"ask": [], "size_ask": [], "timestamp_ask": [], "client_ask": []}
        ).cast(
            {
                "ask": pl.Float64,
                "size_ask": pl.Float64,
                "timestamp_ask": pl.Datetime,
                "client_ask": pl.Boolean,
            }
        )

    def get_base_pricing(
        self,
        base_date: datetime,
        fair_price: float,
        spread: float,
        alpha: float = None,
        bid_sizes: list[float] = None,
        ask_sizes: list[float] = None,
    ) -> pl.DataFrame:
        """Generates the base pricing order book

        Args:
            fair_price (float): The actual fair price
            spread (float): The bid-ask spread
            alpha (float, optional): Parameter that adjust the mid and fair prices difference based on the liquidity. Defaults to None.
            bid_sizes (list[float], optional): A list with all the bid sizes. Defaults to None.
            ask_sizes (list[float], optional): A list with all the ask sizes. Defaults to None.

        Returns:
            pl.DataFrame: Return the order book
        """
        # TODO Change the bid/ask computation based on the functions in utils
        # Define default parameter values
        if bid_sizes is None:
            bid_sizes_ok = [100_000] * 5 + [500_000] + [1_000_000] * (self.n_levels - 6)
        else:
            bid_sizes_ok = bid_sizes.copy()
        if ask_sizes is None:
            ask_sizes_ok = [100_000] * 5 + [500_000] + [1_000_000] * (self.n_levels - 6)
        else:
            ask_sizes_ok = ask_sizes.copy()
        # TODO Alpha should be a list with a different value for each level linked to the size
        if alpha is None:
            alpha_ok = (sum(ask_sizes_ok) - sum(bid_sizes_ok)) / (
                sum(ask_sizes_ok) + sum(bid_sizes_ok)
            )
        else:
            alpha_ok = alpha

        # Compute Bid levels
        bid_prices = [
            fair_price * ((1 - alpha_ok * spread - spread / 2) ** (i + 1))
            for i in range(self.n_levels)
        ]
        # compute datetimes to use
        bid_timestamps = [base_date for _ in range(self.n_levels)]

        new_bids = pl.DataFrame(
            {
                "bid": bid_prices,
                "size_bid": bid_sizes_ok,
                "timestamp_bid": bid_timestamps,
                "client_bid": [False] * self.n_levels,
            }
        ).cast(
            {
                "bid": pl.Float64,
                "size_bid": pl.Float64,
                "timestamp_bid": pl.Datetime,
                "client_bid": pl.Boolean,
            }
        )
        self.bids = (
            pl.concat([self.bids, new_bids], how="vertical")
            .sort("bid", descending=True)
            .head(self.n_levels)
        )
        # Compute Ask levels
        ask_prices = [
            fair_price * ((1 - alpha_ok * spread + spread / 2) ** (i + 1))
            for i in range(self.n_levels)
        ]
        # compute datetimes asks
        ask_timestamps = [base_date for _ in range(self.n_levels)]
        new_asks = pl.DataFrame(
            {
                "ask": ask_prices,
                "size_ask": ask_sizes_ok,
                "timestamp_ask": ask_timestamps,
                "client_ask": [False] * self.n_levels,
            }
        ).cast(
            {
                "ask": pl.Float64,
                "size_ask": pl.Float64,
                "timestamp_ask": pl.Datetime,
                "client_ask": pl.Boolean,
            }
        )
        self.asks = (
            pl.concat([self.asks, new_asks], how="vertical")
            .sort("ask")
            .head(self.n_levels)
        )
        return self.get_order_book()

    def update_order(
        self,
        price: float,
        size: float,
        side: Literal["bid", "ask"],
        client: bool = False,
    ):
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
            self.bids = self.bids.filter(
                self.bids["bid"] != price
            )  # we remove the old bids at the same price
            if size > 0:
                new_order = pl.DataFrame(
                    {
                        "bid": [price],
                        "size_bid": [size],
                        "timestamp_bid": [datetime.now()],
                        "client_bid": [client],
                    }
                ).cast(
                    {
                        "bid": pl.Float64,
                        "size_bid": pl.Float64,
                        "timestamp_bid": pl.Datetime,
                        "client_bid": pl.Boolean,
                    }
                )
                self.bids = (
                    pl.concat([self.bids, new_order], how="vertical")
                    .sort("bid", descending=True)
                    .head(self.n_levels)
                )

        elif side == "ask":
            self.asks = self.asks.filter(
                self.asks["ask"] != price
            )  # removing old asks at the same price
            if size > 0:
                new_order = pl.DataFrame(
                    {
                        "ask": [price],
                        "size_ask": [size],
                        "timestamp_ask": [datetime.now()],
                        "client_ask": [client],
                    }
                ).cast(
                    {
                        "ask": pl.Float64,
                        "size_ask": pl.Float64,
                        "timestamp_ask": pl.Datetime,
                        "client_ask": pl.Boolean,
                    }
                )
                self.asks = (
                    pl.concat([self.asks, new_order], how="vertical")
                    .sort("ask")
                    .head(self.n_levels)
                )

    def get_best_bid(self) -> tuple:
        """Returns the best bid price, size and timestamp."""
        return (
            (
                self.bids["bid"][0],
                self.bids["size_bid"][0],
                self.bids["timestamp_bid"][0],
                self.bids["client_bid"][0],
            )
            if len(self.bids)
            else (None, None, None, None)
        )

    def get_best_ask(self) -> tuple:
        """Returns the best ask price and size."""
        return (
            (
                self.asks["ask"][0],
                self.asks["size_ask"][0],
                self.asks["timestamp_ask"][0],
                self.asks["client_ask"][0],
            )
            if len(self.asks)
            else (None, None, None, None)
        )

    def delete_order(self, price: float, size: float, side: Literal["bid", "ask"]):
        """deletes a specific order from the order book

        Args:
            price (float): price of the order to delete
            size (float): size of the order to delete
            side (str): side of the order to delete. should be either 'bid' or 'ask'

        Raises:
            Exception: if the side is not correctly specified as 'bid' or 'ask'
        """
        side = side.strip().lower()
        if side != "bid" and side != "ask":
            raise Exception("Input a valid side argument : either 'bid' or 'ask'.")

        if side == "ask":
            self.asks = self.asks.filter(
                (self.asks["ask"] != price) & (self.asks["size_ask"] != size)
            )  # removing order
        elif side == "bid":
            self.bids = self.bids.filter(
                (self.bids["bid"] != price) & (self.bids["size_bid"] != size)
            )

    def get_order_book(self) -> pl.DataFrame:
        """Returns the full order book as a Polars DataFrame with the correct column order."""
        # Add index columns for joining
        asks_indexed = self.asks.with_row_index()
        bids_indexed = self.bids.with_row_index()

        # Join on index to align rows
        order_book = asks_indexed.join(bids_indexed, on="index", how="outer").drop(
            "index"
        )

        # Ensure correct column order & type handling
        return order_book.select(
            pl.col("client_bid").cast(pl.Boolean),
            pl.col("timestamp_bid").cast(pl.Datetime),
            pl.col("size_bid").cast(pl.Float64),
            pl.col("bid").cast(pl.Float64),
            pl.col("ask").cast(pl.Float64),
            pl.col("size_ask").cast(pl.Float64),
            pl.col("timestamp_ask").cast(pl.Datetime),
            pl.col("client_ask").cast(pl.Boolean),
        )
