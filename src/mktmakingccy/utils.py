from datetime import datetime, date
import values as vl
import numpy as np
import polars as pl
import random
from trade import TradeHistory


#TODO Changer la dynamic pour faire apparaitre les taux d'interets ????
def simulate_fair_price(
    start_timestamp: datetime = datetime(2025, 1, 1),
    end_timestamp: datetime = datetime(2026, 1, 1),
    step_size_in_seconds: int = 3600,
    mu: float = 0.00001,
    sigma: float = 0.005,
    mu_jump: float = 0.005,
    sigma_jump: float = 0.01,
    jump_lambda: float = 0.005,
    theta: float = 0.05,
    mu_X: float = 0,
    sigma_X: float = 0.01,
    initial_price: float = 100.0,
    min_value: float = 0.001,
) -> pl.DataFrame:
    """Function to simulate and generate time series of the evolution of the price of an emerging currency against USD.

    Args:
        start_timestamp (datetime): The first date of the time series
        end_timestamp (datetime): The last date of the time series
        step_size_in_seconds (int): Time step between two values of the time series
        mu (float, optional): Drift coefficient (Long term trend). Defaults to 0.0001.
        sigma (float, optional): Volatility coefficient of the FX rate. Defaults to 0.02.
        mu_jump (float, optional): Mean jump size of the FX rate. Defaults to 0.01.
        sigma_jump (float, optional): Standard Deviation Jump. Defaults to 0.05.
        jump_lambda (float, optional): Poisson Jump Intensity (Average jumps per step). Defaults to 0.01.
        theta (float, optional): Mean-reversion speed. Defaults to 0.05.
        mu_X (float, optional): Long term mean of the mean-reverting component. Defaults to 0.
        sigma_X (float, optional): Volatility of the mean-reverting component. Defaults to 0.01.
        initial_price (float, optional): Initial FX rate value. Defaults to 1.0.

    Returns:
        pd.DataFrame: The generated time series
    """

    timestamps = pl.datetime_range(
        start=start_timestamp,
        end=end_timestamp,
        interval=f"{step_size_in_seconds}s",
        eager=True,
    )
    N = len(timestamps)
    dt = step_size_in_seconds / (24 * 3600)  # Convert to fraction of a day

    prices = np.zeros(N)
    prices[0] = initial_price
    X_t = 0  # Initial mean-reverting component

    for t in range(1, N):
        dW = np.random.normal(0, np.sqrt(dt))
        dX = theta * (mu_X - X_t) * dt + sigma_X * dW  # Mean-reverting process
        X_t += dX

        # Jump component
        if np.random.rand() < jump_lambda * dt:
            J_t = np.random.normal(mu_jump, sigma_jump)
        else:
            J_t = 0

        # Price evolution (GBM + Jump + Mean Reversion)
        prices[t] = max(
            prices[t - 1] * (1 + mu * dt + sigma * dW) + J_t + X_t, min_value
        )

    return pl.DataFrame({"timestamp": timestamps, "Fair Price": prices})


def compute_volume_history(trade_history: TradeHistory, date: date) -> float:
    return (
        pl.DataFrame(trade_history.trades)
        .filter(pl.col('timestamp').dt.date().eq(date))
        .select('size').sum().item()
    )


def expanding_std(series: np.ndarray) -> list:
    """Function to compute the stdv each row of the DF from the beginning of the DF

    Args:
        series (np.ndarray): The col to use for the stdv

    Returns:
        list: The col of the stdv
    """
    result = [None]
    for i in range(2, len(series) + 1):
        std = np.std(series[1:i])
        result.append(std)
    return result


def compute_all_bid_ask(
    historical_fair_price: pl.DataFrame,
    volume=0, #TODO Change l'argument pour que ça marche avec la fonction history volume
    lambda_val: float = 2,
    bid_asymetry: float = 0.5,
) -> pl.DataFrame:
    """Compute teh bid and ask for all the time steps. For each fair price we will haev a bid ask based on the traded volume

    Args:
        historical_fair_price (_type_, optional): The traded volume during the day. We need it to adapt our spread depending the trades of the day. Defaults to 0, #TODO Change l'argumentpourqueçamarcheaveclafonctionhistoryvolumelambda_val:float=2.
        bid_asymetry (float, optional): In case we want to have a bid (or ask) more wide than ask (or bid). Defaults to 0.5.

    Returns:
        pl.DataFrame: The DF with all the bid ask
    """
    df = historical_fair_price.clone()
    df = df.rename({"Fair Price": "fair_price"})
    df = df.with_columns(
        [
            (pl.col("fair_price").log() - pl.col("fair_price").log().shift(1)).alias(
                "log_return"
            )
        ]
    )
    vol = expanding_std(df["log_return"].to_numpy())
    df = df.with_columns([pl.Series("volatility", vol)])
    df = df.with_columns([(lambda_val * pl.col("volatility")).alias("spread")])
    df = df.with_columns(
        [
            (
                pl.col("fair_price")
                - pl.col("spread")
                * bid_asymetry
                * (1 + volume/sum(vl.VOLUME_LIST)) #TODO change the volume by the value of the function history volume 
            ).alias("bid"),
            (
                pl.col("fair_price")
                + pl.col("spread")
                * (1 - bid_asymetry)
                * (1 + volume/sum(vl.VOLUME_LIST)) #TODO change the volume by the value of the function history volume
            ).alias("ask"),
        ]
    )
    return df


def compute_one_new_bid(
    fair_price: float,
    old_bid: float,
    size #TODO faire en sorte de recuperer la taille du trade pour calculer le nouveau spread
):
    spread = fair_price - old_bid
    new_bid = fair_price - spread * (1 + size/sum(vl.VOLUME_LIST)) #TODO eventuellement changer pour que ce soit en accord avec history volume
    return new_bid

def compute_one_new_ask(
    fair_price: float,
    old_ask: float,
    size #TODO faire en sorte de recuperer la taille du trade pour calculer le nouveau spread
):
    spread = old_ask - fair_price
    new_ask = fair_price + spread * (1 + size/sum(vl.VOLUME_LIST)) #TODO eventuellement changer pour que ce soit en accord avec history volume
    return new_ask


def generate_market_order(
    historical_bid_ask: pl.DataFrame,
    spread_sensibility: float=5,
    base_intensity: float=1,
) -> pl.DataFrame:
    """Generate randomly the market order that will occur at each time step based on the spread (so the volatility indirectly)

    Args:
        historical_bid_ask (pl.DataFrame): The DF containing all the bid ask
        spread_sensibility (float, optional): The impact of the spread to the probabilities. Defaults to 5.
        base_intensity (float, optional): Case of a 0 spread. Defaults to 1.

    Returns:
        pl.DataFrame: The DF with all the probabilities
    """
    df = historical_bid_ask.clone()

    df = df.with_columns([
        ((pl.col("fair_price") - pl.col("bid"))).alias("delta_bid"),
        ((pl.col("ask") - pl.col("fair_price"))).alias("delta_ask"),
    ])

    df = df.with_columns([
        (base_intensity * pl.col("delta_bid").map_elements(lambda x: np.exp(-spread_sensibility * x))).alias("lambda_bid"),
        (base_intensity * pl.col("delta_ask").map_elements(lambda x: np.exp(-spread_sensibility * x))).alias("lambda_ask"),
    ])

    df = df.with_columns([
        (1 - pl.col("lambda_bid").map_elements(lambda x: np.exp(-x))).alias("prob_trade_bid"),
        (1 - pl.col("lambda_ask").map_elements(lambda x: np.exp(-x))).alias("prob_trade_ask"),
    ])

    return df.select(historical_bid_ask.columns + ["prob_trade_bid", "prob_trade_ask"])



def track_pnl(
    historical_fair_price: pl.DataFrame,
    historical_trade: pl.DataFrame,
    inventory: int,
    start_record_time: datetime = None,
    end_record_time: datetime = None,
) -> pl.DataFrame:
    #TODO add the impact of the FX to the PNL with the inventory
    if start_record_time is None:
        start_record_time = historical_trade[0, "timestamp"]
    if end_record_time is None:
        end_record_time = historical_trade[-1, "timestamp"]
    masked_historical_trade = historical_trade.filter(
        pl.col("timestamp").is_between(start_record_time, end_record_time)
    )
    total_pnl = 0
    records = []

    for trade_row in masked_historical_trade.iter_rows(named=True):
        action = trade_row["side"]
        trade_price = trade_row["price"]
        quantity = trade_row["size"]
        trade_date = trade_row["timestamp"]
        closest_price_row = (
            historical_fair_price.filter(pl.col("timestamp") <= trade_date)
            .sort("timestamp", descending=True)
            .head(1)
        )
        price = closest_price_row[0, "Fair Price"]

        sign = 1 if action == "buy" else -1
        inventory -= sign * quantity
        pnl = sign * (quantity / price) * (trade_price - price) #juste diviser par price pour PNL en $ ??
        total_pnl += pnl

        records.append(
            {"timestamp": trade_date, "pnl": total_pnl, "inventory": inventory}
        )
    result_df = pl.DataFrame(records)
    return result_df
