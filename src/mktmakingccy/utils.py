from datetime import datetime

import numpy as np
import polars as pl


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
    initial_price: float = 1.0,
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


def track_pnl(
    historical_fair_price: pl.DataFrame,
    historical_trade: pl.DataFrame,
    inventory,
    start_record_time: datetime = None,
    end_record_time: datetime = None,
) -> pl.DataFrame:
    if start_record_time is None:
        start_record_time = historical_trade[0, "timestamp"]
    if end_record_time is None:
        end_record_time = historical_trade[-1, "timestamp"]
    masked_historical_trade = historical_trade.filter(
        pl.col("timestamp").is_between(start_record_time, end_record_time)
    )
    total_pnl = 0
    records = []

    for trade_row in masked_historical_trade.iter_rows():
        action = trade_row[0]
        trade_price = trade_row[1]
        quantity = trade_row[2]
        trade_date = trade_row[3]
        closest_price_row = (
            historical_fair_price.filter(pl.col("timestamp") <= trade_date)
            .sort("timestamp", descending=True)
            .head(1)
        )
        price = closest_price_row[0, "Fair Price"]

        sign = 1 if action == "buy" else -1
        inventory -= sign * quantity
        pnl = sign * quantity * (trade_price - price)
        total_pnl += pnl

        records.append(
            {"timestamp": trade_date, "pnl": total_pnl, "inventory": inventory}
        )
    result_df = pl.DataFrame(records)
    return result_df
