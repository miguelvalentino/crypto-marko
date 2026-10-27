"""Logika portofolio: optimasi bobot Markowitz dan simulasi modal.

Modul ini murni perhitungan (tanpa Streamlit) agar mudah dibaca dan diuji.
"""

from dataclasses import dataclass

import numpy as np

# Langkah grid search bobot (1%).
WEIGHT_STEP = 0.01

# Toleransi pembulatan agar bobot yang jumlahnya 1.0 tetap lolos pengecekan.
EPSILON = 1e-9


@dataclass
class PortfolioResult:
    """Hasil optimasi portofolio dengan Sharpe ratio tertinggi."""

    weights: list[float]
    expected_return: float
    risk: float
    sharpe: float


@dataclass
class SimulationRow:
    """Rincian alokasi dana untuk satu aset."""

    asset: str
    weight: float
    units: float
    final_value: float
    profit: float


@dataclass
class SimulationResult:
    """Ringkasan hasil simulasi modal."""

    rows: list[SimulationRow]
    total_value: float
    total_profit: float


def portfolio_return(weights, expected_returns):
    """Expected return portofolio: jumlah (bobot x return aset)."""
    return sum(weights[i] * expected_returns[i] for i in range(3))


def portfolio_variance(weights, covariance):
    """Varians portofolio: w^T x Cov x w."""
    return sum(
        weights[i] * weights[j] * covariance[i][j]
        for i in range(3)
        for j in range(3)
    )


def optimize_weights(mu, cov, risk_free, min_weight, step=WEIGHT_STEP):
    """Cari bobot dengan Sharpe ratio tertinggi lewat grid search.

    Args:
        mu: expected return tiap aset (array 3 nilai).
        cov: matriks covariance 3x3.
        risk_free: risk-free rate untuk horizon terpilih.
        min_weight: bobot minimum per aset (fraksi, misal 0.20).
        step: jarak grid search (default 1%).

    Returns:
        PortfolioResult berisi bobot terbaik beserta return, risiko, dan Sharpe.
    """
    mu = np.asarray(mu)
    cov = np.asarray(cov)

    max_weight = 1 - 2 * min_weight

    best_sharpe = -float("inf")
    best_weights = [1 / 3, 1 / 3, 1 / 3]

    for w_btc in np.arange(min_weight, max_weight + EPSILON, step):
        for w_eth in np.arange(min_weight, max_weight + EPSILON, step):
            w_sol = 1 - w_btc - w_eth
            if w_sol < min_weight - EPSILON or w_sol > max_weight + EPSILON:
                continue

            weights = [w_btc, w_eth, w_sol]
            exp_return = portfolio_return(weights, mu)
            variance = portfolio_variance(weights, cov)
            std_dev = max(0, variance) ** 0.5
            sharpe = (exp_return - risk_free) / std_dev if std_dev > 0 else 0

            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_weights = weights

    return PortfolioResult(
        weights=best_weights,
        expected_return=portfolio_return(best_weights, mu),
        risk=max(0, portfolio_variance(best_weights, cov)) ** 0.5,
        sharpe=best_sharpe,
    )


def simulate_portfolio(asset_data, weights, capital):
    """Hitung alokasi dana dan nilai akhir portofolio berdasarkan prediksi.

    Args:
        asset_data: dict {kode aset: {"last": harga, "pred": harga prediksi}}.
        weights: bobot tiap aset sesuai urutan ``asset_data``.
        capital: modal awal dalam rupiah.

    Returns:
        SimulationResult berisi rincian per aset serta total nilai dan laba.
    """
    rows = []
    total_value = 0.0

    for i, (asset, data) in enumerate(asset_data.items()):
        weight = weights[i]
        allocation = capital * weight
        units = allocation / data["last"] if data["last"] else 0
        final_value = units * data["pred"]
        total_value += final_value

        rows.append(
            SimulationRow(
                asset=asset,
                weight=weight,
                units=units,
                final_value=final_value,
                profit=final_value - allocation,
            )
        )

    return SimulationResult(
        rows=rows,
        total_value=total_value,
        total_profit=total_value - capital,
    )
