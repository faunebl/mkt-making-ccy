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

    return pl.DataFrame({"Timestamp": timestamps, "Fair Price": prices})


def track_pnl(
    start_record_time: datetime,
    end_record_time: datetime,
    historical_fair_price: pl.DataFrame,
    historical_trade: pl.DataFrame,
) -> pl.DataFrame:
    # TODO change the column name "date"
    masked_historical_fair_price = historical_fair_price.filter(
        pl.col("date") >= start_record_time & pl.col("date") <= end_record_time
    )
    masked_historical_trade = historical_trade.filter(
        pl.col("date") >= start_record_time & pl.col("date") <= end_record_time
    )
    
