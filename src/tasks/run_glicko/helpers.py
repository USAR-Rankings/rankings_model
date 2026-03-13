import math
import random
import itertools
from typing import Any, Dict, List, Tuple, Optional
import numpy as np
import pandas as pd


def g(phi: float) -> float:
    """Glicko-2 g() function; phi in Glicko internal units."""
    return 1.0 / math.sqrt(1.0 + (3.0 * phi * phi) / (math.pi ** 2))

def E(mu: float, mu_j: float, phi_j: float) -> float:
    """Expected score (logistic approximation using g(phi_j))."""
    return 1.0 / (1.0 + math.exp(-g(phi_j) * (mu - mu_j)))

def calculate_win_prob(elo1: float, elo2: float) -> float:
    """Classic Elo probability on 400 scale (kept for backward compatibility)."""
    return 1.0 / (1.0 + math.pow(10.0, (elo1 - elo2) / 400.0))

def calculate_team_rating_certainty_weighted(players: List[Any]) -> Tuple[float, float, List[float]]:
    """
    Certainty-weighted team rating in Glicko internal units (mu, phi).
    Returns (team_mu, team_phi, weights) where phi is computed as sqrt(1/sum(1/phi_i^2))
    — caution: inverse-variance pooling can produce small phi; the GLICKO_ADD
    model offers other team methods and clamps.
    """
    inv_phi_squared_sum = sum(1.0 / (p.phi ** 2 + 1e-12) for p in players)
    weights = [1.0 / (p.phi ** 2 + 1e-12) / inv_phi_squared_sum for p in players]
    team_mu = sum(w * p.mu for w, p in zip(weights, players))
    team_phi = math.sqrt(1.0 / inv_phi_squared_sum)
    return team_mu, team_phi, weights

def expected_match_delta(mu, phi, opp_phi, score, expected):
    """
    Legacy-style expected match delta (approx). Provided for logging compatibility.
    This is not used for the per-player Glicko updates in the ADD model — we use
    per-player delta = g(opp_phi) * (s - E_player).
    """
    g_opp = g(opp_phi)
    denom = 1 + (phi**2) * (g_opp**2) * expected * (1.0 - expected)
    return (phi**2 * g_opp / denom) * (score - expected)
