import math
import random
import itertools
from typing import Any, Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from src.tasks.run_glicko.helpers import * 

# -------------------------
# Player_ADD
# -------------------------
class Player_ADD:
    """
    Glicko-2 Player used by GLICKO_ADD. Stores:
      - mu, phi, sigma (internal units)
      - per-tournament buffered match evidence as (delta, g_op, E, v)
    """

    def __init__(
        self,
        name: str,
        time_since_play: int = 0,
        games: int = 0,
        starting_rating: float = 1500.0,
        starting_rd: float = 350.0,
        starting_sigma: float = 0.06,
        glicko_scale: float = 173.7178,
        tau: float = 0.5,
        time_constant: float = 0.4,
        convexity: float = 1.75,
        rd_min: float = 50.0,
        rd_max: float = 350.0,
        max_reduction_frac: float = 0.15,
        cap_redux=False,
        rd_inflation_mode: str = "power",
        buffer_days: float = 0.0,
        decay_tau_days: float = 90.0,
        sat_power: float = 1.0,
        provisional: bool = False,
        provisional_min_tournaments: int = 2,
        provisional_min_games: int = 8,
        cap_provisional_update: bool = False,
        provisional_cap_first_gain_elo: float = 75.0,
        provisional_cap_second_gain_elo: float = 110.0,
    ):
        self.name = name
        self.glicko_scale = glicko_scale
        self.tau = tau

        # internal Glicko units
        self.mu = (starting_rating - 1500.0) / self.glicko_scale
        self.phi = starting_rd / self.glicko_scale
        self.sigma = starting_sigma

        # clamps
        self.phi_min = rd_min / self.glicko_scale
        self.phi_max = rd_max / self.glicko_scale
        self.time_constant = time_constant
        self.convexity = convexity

        # buffers & bookkeeping
        self._team_results: List[Tuple[float, float, float, float]] = []
        self.highest_division = 10
        self.entry_division = None
        self.last_division = None
        self.games = games
        self.tournies: List[str] = []
        self.days_since_played = time_since_play
        self.last_played = None
        self.phi_last = self.phi
        self.max_reduction_frac = max_reduction_frac
        self.cap_redux = cap_redux
        self.rd_inflation_mode = rd_inflation_mode
        self.buffer_days = float(buffer_days)
        self.decay_tau_days = float(decay_tau_days)
        self.sat_power = float(sat_power)

        self.provisional = bool(provisional)
        self.provisional_min_tournaments = int(provisional_min_tournaments)
        self.provisional_min_games = int(provisional_min_games)
        self.cap_provisional_update = bool(cap_provisional_update)
        self.provisional_cap_first_gain_elo = float(provisional_cap_first_gain_elo)
        self.provisional_cap_second_gain_elo = float(provisional_cap_second_gain_elo)

        self.entry_rating = float(starting_rating)

    @property
    def rating(self) -> float:
        return 1500.0 + self.mu * self.glicko_scale

    @property
    def RD(self) -> float:
        return self.phi * self.glicko_scale

    @property
    def tournaments_played(self) -> int:
        return len(set(self.tournies))

    def refresh_provisional_status(self):
        """
        Strict rule:
        stay provisional until BOTH thresholds are met.
        """
        if not self.provisional:
            return

        min_t = max(0, int(self.provisional_min_tournaments))
        min_g = max(0, int(self.provisional_min_games))

        enough_tournaments = (self.tournaments_played >= min_t) if min_t > 0 else True
        enough_games = (self.games >= min_g) if min_g > 0 else True

        self.provisional = not (enough_tournaments and enough_games)
    # -------------------------
    # Tournament interaction
    # -------------------------
    def add_game(self, opponent_mu: float, opponent_phi: float, score: int):
        # legacy; not used by ADD main flow (we use add_team_result)
        self._team_results.append((opponent_mu, opponent_phi, score))
        self.games += 1

    def add_tourney(self, tourney: str):
        self.tournies.append(tourney)

    def add_division(self, div: int):
        """
        Track three division notions:
        - entry_division: first division ever seen
        - last_division: most recent division seen
        - highest_division: best/highest division ever seen (lower code = higher division)
        """
        if self.entry_division is None:
            self.entry_division = div

        self.last_division = div
        self.highest_division = min(self.highest_division, div)

    def update_days_last_played(self, date):
        """
        Compute days_since_played as days between `date` (next tournament date)
        and previously recorded last_played.

        Behavior:
         - If last_played is None, set days_since_played to a large value (365)
           so new/long-idle players inflate toward phi_max if desired.
         - Otherwise set to integer day difference.
        """
        if self.last_played is None:
            # treat as long inactivity so update_rd can inflate (tunable)
            self.days_since_played = 0
        else:
            try:
                # date and last_played expected to be pd.Timestamp or datetime.date-like
                self.days_since_played = abs((date - self.last_played).days)
            except Exception:
                # safe fallback if types mismatch
                self.days_since_played = 0

    def update_time(self, date):
        """
        Only update the last_played timestamp. Do NOT modify days_since_played here.
        This preserves the computed gap for update_rd() which must be called
        AFTER update_days_last_played(date) and BEFORE update_time(date).
        """
        self.last_played = date

    def update_rd(self):
        """
        Age RD (phi) based on days_since_played and phi_last.

        Modes:
        - "power" (default): legacy convexity-based power law (backward compatible)
        - "saturating": saturating exponential after optional buffer_days

        buffer_days:
        - If >0, no inflation for the first `buffer_days` of inactivity.
        """
        days = float(self.days_since_played)

        # --- apply optional grace buffer ---
        if self.buffer_days > 0.0:
            eff_days = max(0.0, days - self.buffer_days)
            if eff_days <= 0.0:
                # within grace period: no inflation
                self.phi = min(self.phi_max, max(self.phi_last, self.phi_min))
                return
        else:
            # backward-compatible: your old code used max(days, 1)
            eff_days = max(days, 1.0)

        if self.rd_inflation_mode in ("power", "convexity"):
            # legacy power law in "years"
            t = eff_days / 365.0
            phi_new = math.sqrt(self.phi_last**2 + (self.time_constant**2) * (t**self.convexity))
            self.phi = min(self.phi_max, phi_new)

        elif self.rd_inflation_mode in ("saturating", "sat"):
            # saturating inflation after buffer:
            # phi^2 <- phi_last^2 + c^2 * (1 - exp(-eff_days / decay_tau_days))^sat_power
            tau_d = max(self.decay_tau_days, 1e-6)
            frac = 1.0 - math.exp(-eff_days / tau_d)
            frac = frac ** max(self.sat_power, 1e-6)
            phi_new = math.sqrt(self.phi_last**2 + (self.time_constant**2) * frac)
            self.phi = min(self.phi_max, phi_new)

        else:
            raise ValueError(f"Unknown rd_inflation_mode={self.rd_inflation_mode}")

        # keep within clamps
        self.phi = max(self.phi_min, min(self.phi, self.phi_max))

    def add_team_result(self, delta: float, g_op: float, E_val: float, v: float):
        """
        Add per-player match evidence:
          delta = g(opponent_phi) * (s - E_player)
          g_op = g(opponent_phi)
          E_val = expected probability for this player
          v = 1 / [g(op)^2 * E * (1-E)] (per-match single-match variance)
        """
        self._team_results.append((delta, g_op, E_val, v))
        self.games += 1

    # -------------------------
    # Volatility solver (Glicko-2)
    # -------------------------
    def _update_volatility(self, delta: float, v: float):
        a = math.log(self.sigma ** 2)
        tau = self.tau
        phi = self.phi

        def f(x):
            ex = math.exp(x)
            num = ex * (delta**2 - phi**2 - v - ex)
            den = 2.0 * (phi**2 + v + ex)**2
            return num / den - (x - a) / (tau**2)

        A = a
        if delta**2 > phi**2 + v:
            B = math.log(delta**2 - phi**2 - v)
        else:
            k = 1
            # ensure loop safety
            while f(a - k * tau) < 0 and k < 1000:
                k += 1
            B = a - k * tau

        fA = f(A)
        fB = f(B)

        # iterative root finding with safety
        iter_count = 0
        while abs(B - A) > 1e-6 and iter_count < 100:
            C = A + (A - B) * fA / (fB - fA)
            fC = f(C)
            if fC * fB < 0:
                A = B
                fA = fB
            else:
                fA = fA / 2.0
            B = C
            fB = fC
            iter_count += 1

        self.sigma = math.exp(A / 2.0)

    # -------------------------
    # Update player at end of tournament
    # -------------------------
    def update_player(self, date):
        """
        Run full Glicko-2 update (volatility solver + phi + mu) using the per-player
        _team_results list of (delta, g_op, E, v). Clears the buffer after updating.
        """
        # No games: update inactivity only
        if not self._team_results:
            self.update_days_last_played(date)
            self.update_rd()
            return

        # snapshot pre-update state for optional provisional gain cap
        pre_rating = self.rating
        was_provisional = bool(getattr(self, "provisional", False))
        completed_tournaments = getattr(self, "tournaments_played", len(set(getattr(self, "tournies", []))))

        # Step 1: accumulate weighted information & delta_sum
        # IMPORTANT: use the stored per-match v so provisional team weighting
        # carries through to phi / volatility as well as mu.
        v_inv = 0.0
        delta_sum = 0.0
        for delta, g_op, E_val, v_match in self._team_results:
            v_inv += 1.0 / max(v_match, 1e-12)
            delta_sum += delta

        # guard
        v_inv = max(v_inv, 1e-12)
        v = 1.0 / v_inv

        # Cap delta_sum if RD large (prevent huge swings)
        RD_elo = self.RD
        if RD_elo >= 180.0:
            max_gain = 0.75 * RD_elo / self.glicko_scale
            delta_sum = max(-max_gain, min(delta_sum, max_gain))

        # Step 2: volatility update
        delta_for_sigma = v * delta_sum
        self._update_volatility(delta_for_sigma, v)

        # Step 3: phi update
        phi_star = math.sqrt(self.phi**2 + self.sigma**2)
        new_phi= 1.0 / math.sqrt((1.0 / (phi_star**2)) + (1.0 / v))
       
        # Cap per-tournament reduction to avoid overconfident collapse
        # If new_phi < phi_last, allow no more than max_reduction_frac fractional drop
        if new_phi < self.phi_last:
            phi_candidate = new_phi
            if self.cap_redux:
                min_allowed = max(self.phi_min, self.phi_last * (1.0 - self.max_reduction_frac))
                phi_candidate = max(phi_candidate, min_allowed)
            self.phi = min(phi_candidate, self.phi_max)
        else:
            self.phi = min(new_phi, self.phi_max)

        # Step 4: mu update
        self.mu += (self.phi**2) * delta_sum

        if was_provisional and self.cap_provisional_update:
            upside_cap = None
            if completed_tournaments <= 1:
                upside_cap = self.provisional_cap_first_gain_elo
            elif completed_tournaments <= 2:
                upside_cap = self.provisional_cap_second_gain_elo

            if upside_cap is not None:
                capped_rating = min(self.rating, pre_rating + upside_cap)
                self.mu = (capped_rating - 1500.0) / self.glicko_scale

        # cleanup & housekeeping
        self._team_results = []
        self.phi = max(self.phi_min, self.phi)
        self.phi_last = self.phi
        self.update_time(date)
        self.days_since_played = 0
        # first tournament completed -> no longer provisional
        if self.provisional:
             self.refresh_provisional_status()
        
        

# -------------------------
# GLICKO_ADD (full-featured)
# -------------------------
class GLICKO_ADD:
    """
    Full-featured Glicko-2 doubles model with selectable team aggregation methods:
      - team_method='sum' : mu_team = sum(mu_i), phi_team = sqrt(sum phi_i^2)
      - team_method='avg' : mu_team = mean(mu_i), phi_team = sqrt(sum phi_i^2)/n
      - team_method='inv_var' : mu_team = inverse-variance pooled; phi_team = clamp(max(raw, gamma*additive))
    This class preserves the major API surface of your original GLICKO_Model.
    """

    def __init__(
        self,
        sep: float = 1500.0,
        p_dict: Optional[Dict[str, Player_ADD]] = None,
        tab: Optional[pd.DataFrame] = None,
        avg_team: bool = False,
        remove: bool = False,
        remove_time: float = 365.0 * 1.5,
        GLICKO_SCALE: float = 173.7178,
        mu_per: float = 33.0,
        time_constant: float = 0.4,
        convexity: float = 1.75,
        tau: float = 0.5,
        rd_min: float = 50.0,
        rd_max: float = 350.0,
        instant_update: bool = False,
        avg_mu: bool = False,
        team_method: str = 'avg',   # 'sum' | 'avg' | 'inv_var'
        inv_var_gamma: float = 0.6, # clamp for inv_var
        de: float = 200.0,          # Expert division offset (tunable)
        dc: float = 250.0,          # Lower division offset (tunable)
        min_existing_for_stat: int = 5,  # minimum players required to use division stat
        avg_mode: str = "mean",
        team_var_alpha: float = 0.5,
        max_reduction_frac: float = 0.15,
        cap_redux=False,
        rd_inflation_mode: str = "power",   # default = legacy convexity curve
        buffer_days: float = 0.0,
        decay_tau_days: float = 90.0,
        sat_power: float = 1.0,
        provisional_tag=False,
        provisional_team_weight=0.35,
        provisional_team_mode="mean",
        provisional_min_tournaments: int = 2,
        provisional_min_games: int = 8,
        provisional_player_weight: float = 0.70,
        cap_provisional_update: bool = False,
        provisional_cap_first_gain_elo: float = 75.0,
        provisional_cap_second_gain_elo: float = 110.0,

        entry_rd: float = 350.0,

        global_entry: bool = False,
        fixed_entry_through_year: int = 2021,
        global_entry_stat_mode: str = "p33",   # "p33" | "median"
        global_entry_refresh_years: int = 1,
        global_entry_min_players: int = 15,
        global_entry_source_map: Optional[Dict[int, int]] = None,
        global_entry_min_tournies: int = 3,
        global_entry_division_basis: str = "highest",
        global_entry_snapshot_mode: str = "first_eligible",

        blend_entry: bool = False,
        blend_existing_k: float = 6.0,
        blend_max_weight: float = 0.85,
        blend_exclude_provisional: bool = True,
        blend_min_div_players: int = 10,

    ):
        self.sep = sep
        self.p_dict = {} if p_dict is None else p_dict
        self.tab = pd.DataFrame() if tab is None else tab
        self.played_games = pd.DataFrame()
        self.predicted_games = pd.DataFrame()
        self.players_total = pd.DataFrame()
        self._div_dict = {0: "Pro", 1: "Premier", 2: "Expert", 3: "Contender"}
        self.avg_team = avg_team
        self.remove = remove
        self.remove_time = remove_time
        self.GLICKO_SCALE = GLICKO_SCALE
        self.mu_per = mu_per
        self.time_constant = time_constant
        self.convexity = convexity
        self.rd_min = rd_min
        self.rd_max = rd_max
        self.tau = tau
        self.instant_update = instant_update
        self.min_existing_for_stat = min_existing_for_stat
        self.de = de
        self.dc = dc
        self.avg_mu = avg_mu
        self.team_method = team_method
        self.inv_var_gamma = inv_var_gamma
        self.avg_mode = avg_mode
        self.team_var_alpha = team_var_alpha
        self.max_reduction_frac = max_reduction_frac
        self.cap_redux=cap_redux
        self.entry_rd = float(entry_rd)
        # sanity
        assert team_method in ('sum', 'avg', 'inv_var')
        self.rd_inflation_mode = rd_inflation_mode
        self.buffer_days = float(buffer_days)
        self.decay_tau_days = float(decay_tau_days)
        self.sat_power = float(sat_power)
        self.provisional_flag = provisional_tag
        self.provisional_team_weight = provisional_team_weight
        self.provisional_team_mode = provisional_team_mode
        self.provisional_min_tournaments = int(provisional_min_tournaments)
        self.provisional_min_games = int(provisional_min_games)
        self.provisional_player_weight = float(provisional_player_weight)
        self.cap_provisional_update = bool(cap_provisional_update)
        self.provisional_cap_first_gain_elo = float(provisional_cap_first_gain_elo)
        self.provisional_cap_second_gain_elo = float(provisional_cap_second_gain_elo)
        

        assert 0.0 < self.provisional_team_weight <= 1.0
        assert 0.0 < self.provisional_player_weight <= 1.0
        assert self.provisional_team_mode in ("mean", "any", "min", "product")
        assert self.entry_rd >= self.rd_min and self.entry_rd <= self.rd_max


        assert self.rd_inflation_mode in ("power", "convexity", "saturating", "sat")
        self.global_entry = bool(global_entry)
        self.fixed_entry_through_year = int(fixed_entry_through_year)
        self.global_entry_stat_mode = str(global_entry_stat_mode).lower()
        self.global_entry_refresh_years = int(global_entry_refresh_years)
        self.global_entry_min_players = int(global_entry_min_players)
        self.global_entry_min_tournies = int(global_entry_min_tournies)
        self.global_entry_division_basis = str(global_entry_division_basis).lower()
        self.global_entry_snapshot_mode = str(global_entry_snapshot_mode).lower()


        # Default men's post-cutoff mapping:
        # Pro -> Pro, Premier -> Expert, Expert -> Expert, Contender -> Contender
        if global_entry_source_map is None:
            self.global_entry_source_map = {0: 0, 1: 2, 2: 2, 3: 3}
        else:
            self.global_entry_source_map = {int(k): int(v) for k, v in global_entry_source_map.items()}

        # Cached global anchors, refreshed on demand
        self._global_entry_cache: Dict[int, float] = {}
        self._global_entry_cache_year: Optional[int] = None
        self._global_entry_cache_history: Dict[int, Dict[int, float]] = {}
        self._global_entry_count_history: Dict[int, Dict[int, int]] = {}

        assert self.global_entry_stat_mode in ("p33", "median")
        assert self.global_entry_refresh_years >= 1
        assert self.global_entry_min_players >= 1
        assert self.global_entry_min_tournies >= 1
        assert self.global_entry_division_basis in ("highest", "last", "entry")
        assert self.global_entry_snapshot_mode in ("first_eligible", "latest_preyear")

        # Blending entry
        self.blend_entry = bool(blend_entry)
        self.blend_existing_k = float(blend_existing_k)
        self.blend_max_weight = float(blend_max_weight)
        self.blend_exclude_provisional = bool(blend_exclude_provisional)
        self.blend_min_div_players = int(blend_min_div_players)

        assert self.blend_existing_k > 0
        assert 0.0 <= self.blend_max_weight <= 1.0
        assert self.blend_min_div_players >= 1


        

    # -------------------------
    # Team stats helpers
    # -------------------------
    def _team_stats_sum(self, players: List[Player_ADD]) -> Tuple[float, float]:
        mus = [p.mu for p in players]
        phis = [p.phi for p in players]
        return sum(mus), math.sqrt(sum(phi*phi for phi in phis))

    def _team_stats_avg(self, players: List[Player_ADD]) -> Tuple[float, float]:
        n = len(players)
        mus = [p.mu for p in players]
        phis = [p.phi for p in players]
        mu = sum(mus) / n
        phi = math.sqrt(sum(phi*phi for phi in phis) / (n*n))
        return mu, phi

    def _team_stats_inv_var(self, players: List[Player_ADD]) -> Tuple[float, float]:
        inv = [1.0 / (p.phi**2 + 1e-12) for p in players]
        inv_sum = sum(inv)
        weights = [x / inv_sum for x in inv]
        mu = sum(w * p.mu for w, p in zip(weights, players))

        # raw inverse-variance pooled phi
        raw_phi = math.sqrt(1.0 / inv_sum)

        # additive uncertainty (root-sum-square of member phis)
        additive_phi = math.sqrt(sum(p.phi**2 for p in players))

        # combined team phi: guard against raw_phi being unrealistically small
        # team_var_alpha in [0,1] blends additive uncertainty into the raw pooled phi.
        phi = math.sqrt(raw_phi**2 + (self.team_var_alpha * additive_phi)**2)

        # optional extra clamp to keep phi >= inv_var_gamma * additive_phi (backwards-compatible)
        phi = max(phi, self.inv_var_gamma * additive_phi)

        return mu, phi

    def _team_stats(self, players: List[Player_ADD]) -> Tuple[float, float]:
        if self.team_method == 'sum':
            return self._team_stats_sum(players)
        elif self.team_method == 'avg':
            return self._team_stats_avg(players)
        else:
            return self._team_stats_inv_var(players)

    def _player_reliability(self, player: Player_ADD) -> float:
        """
        Reliability used when this player's team is the *opponent*.
        Established players count as 1.0; provisional players count less.
        """
        return self.provisional_team_weight if getattr(player, "provisional", False) else 1.0

    def _team_reliability(self, players: List[Player_ADD]) -> float:
        """
        Converts player-level provisional status into team-level reliability.
        Recommended default: mode='mean'
          - one provisional + one established -> moderate discount
          - both provisional -> strong discount
        """
        player_rels = [self._player_reliability(p) for p in players]
        provisional_flags = [getattr(p, "provisional", False) for p in players]

        if self.provisional_team_mode == "any":
            return self.provisional_team_weight if any(provisional_flags) else 1.0
        elif self.provisional_team_mode == "mean":
            return float(sum(player_rels) / len(player_rels))
        elif self.provisional_team_mode == "min":
            return float(min(player_rels))
        elif self.provisional_team_mode == "product":
            out = 1.0
            for r in player_rels:
                out *= r
            return float(out)
        else:
            raise ValueError(f"Unknown provisional_team_mode={self.provisional_team_mode}")

    def _parse_division_code(self, division: str) -> int:
        division = str(division).upper()
        if ("PREMIER" in division) or ("PRO" in division):
            return 0 if "PRO" in division else 1
        elif any(x in division for x in ["EXPERT", "ELITE", "ADVANCED", "GOLD", "WOMEN"]):
            return 2
        else:
            return 3

    def _fixed_baseline_for_div(self, div: int) -> float:
        if div in (0, 1):
            return self.sep
        elif div == 2:
            return self.sep - self.de
        else:
            return self.sep - self.dc

    def _legacy_local_starting_mu(self, player_array: List[str], baseline_mu: float) -> float:
        """
        Existing behavior for local/tournament-specific starts when avg_mu=True.
        Kept unchanged for women's mode or pre-cutoff years.
        """
        starting_mu = baseline_mu
        existing_mus = [self.p_dict[p].rating for p in player_array if p in self.p_dict]

        if len(existing_mus) >= max(1, int(self.min_existing_for_stat)):
            if self.avg_mode == "mean":
                starting_mu = float(np.mean(existing_mus))
            elif self.avg_mode in ("pct33", "p33", "33"):
                starting_mu = float(np.percentile(existing_mus, 33))
            elif self.avg_mode in ("median", "50", "pct50"):
                starting_mu = float(np.percentile(existing_mus, 50))
            else:
                starting_mu = float(np.percentile(existing_mus, 50))

        return starting_mu

    def _should_use_global_entry_logic(self, date) -> bool:
        """
        New division-entry logic only applies when womens=False and the season/year
        is after the fixed-baseline era.
        """
        if self.global_entry==False:
            return False
        year = pd.Timestamp(date).year
        return year > self.fixed_entry_through_year

    def _compute_global_entry_stat(self, ratings: List[float]) -> float:
        if self.global_entry_stat_mode == "median":
            return float(np.median(ratings))
        return float(np.percentile(ratings, 33))

    def _refresh_global_entry_cache(self, date, force: bool = False):
        """
        Compute annual global division anchors from historical snapshots, not just active players.

        For anchor year Y:
        - use players_total rows with Date < Jan 1 of Y
        - require Tournaments_Played >= global_entry_min_tournies
        - keep the latest eligible snapshot per player before Y
        - group by the selected division basis
        - compute anchor + contributor counts
        """
        year = pd.Timestamp(date).year

        if (not force) and (self._global_entry_cache_year is not None):
            if year < (self._global_entry_cache_year + self.global_entry_refresh_years):
                return

        cutoff_date = pd.Timestamp(year=year, month=1, day=1)

        new_cache: Dict[int, float] = {}
        new_counts: Dict[int, int] = {}

        use_historical = (
            hasattr(self, "players_total") and
            isinstance(self.players_total, pd.DataFrame) and
            (not self.players_total.empty)
        )

        if use_historical:
            hist = self.players_total.copy()

            if "Date" not in hist.columns:
                use_historical = False
            else:
                hist["Date"] = pd.to_datetime(hist["Date"], errors="coerce")
                basis_col = self._global_entry_basis_col()

                if basis_col not in hist.columns:
                    use_historical = False

        if use_historical:
            hist = hist.loc[
                (hist["Date"].notna()) &
                (hist["Date"] < cutoff_date) &
                (hist["Tournaments_Played"] >= self.global_entry_min_tournies)
            ].copy()

            if not hist.empty:
                if self.global_entry_snapshot_mode == "first_eligible":
                    # Freeze each player's contribution at the first time they become established
                    hist = hist.sort_values(["name", "Tournaments_Played", "Date", "rating"])
                    hist = hist.drop_duplicates(subset=["name"], keep="first")
                else:
                    # Old behavior: latest eligible pre-year snapshot
                    hist = hist.sort_values(["name", "Date", "Tournaments_Played", "rating"])
                    hist = hist.drop_duplicates(subset=["name"], keep="last")

                hist["division_code"] = self._global_entry_basis_divcode(
                    hist[self._global_entry_basis_col()]
                )

                for div in [0, 1, 2, 3]:
                    vals = hist.loc[hist["division_code"] == div, "rating"].dropna().tolist()
                    n = len(vals)
                    if n >= self.global_entry_min_players:
                        new_cache[div] = self._compute_global_entry_stat(vals)
                        new_counts[div] = n

        # fallback if no historical snapshots exist yet for this year
        if len(new_cache) == 0:
            ratings_by_div = {0: [], 1: [], 2: [], 3: []}

            for player in self.p_dict.values():
                if not self._player_is_established_for_global_entry(player):
                    continue

                basis = getattr(self, "global_entry_division_basis", "highest").lower()
                if basis == "entry":
                    div = getattr(player, "entry_division", None)
                elif basis == "last":
                    div = getattr(player, "last_division", None)
                else:
                    div = getattr(player, "highest_division", None)

                if div in ratings_by_div:
                    ratings_by_div[div].append(player.rating)

            for div, ratings in ratings_by_div.items():
                if len(ratings) >= self.global_entry_min_players:
                    new_cache[div] = self._compute_global_entry_stat(ratings)
                    new_counts[div] = len(ratings)

        self._global_entry_cache = new_cache
        self._global_entry_cache_year = year
        self._global_entry_cache_history[year] = dict(new_cache)
        self._global_entry_count_history[year] = dict(new_counts)


    def _global_starting_mu(self, div: int, date) -> float:
        """
        Post-cutoff global anchor. Uses source-map indirection so you can make
        Premier and Expert both use Expert-only entry.
        """
        self._refresh_global_entry_cache(date)

        source_div = self.global_entry_source_map.get(div, div)

        # If the requested source division is missing, recompute once in case the pool changed
        if source_div not in self._global_entry_cache:
            self._refresh_global_entry_cache(date, force=True)

        if source_div in self._global_entry_cache:
            return self._global_entry_cache[source_div]

        # Fallback to the fixed baseline of the SOURCE division, not the target division.
        # This is important for Premier -> Expert mapping after cutoff.
        return self._fixed_baseline_for_div(source_div)

    def _player_is_established_for_global_entry(self, player: Player_ADD) -> bool:
        """
        A player counts toward the yearly global entry anchor only if they are established.
        Current definition: at least `global_entry_min_tournies` tournaments played.
        """
        return len(getattr(player, "tournies", [])) >= self.global_entry_min_tournies

    def _get_player_anchor_division(self, player: Player_ADD) -> Optional[int]:
        """
        Which division label should this player contribute to when building the
        yearly global entry anchor cache?
        - 'highest' -> highest_division
        - 'last'    -> last_division
        - 'entry'   -> entry_division
        """
        if self.global_entry_division_basis == "highest":
            return getattr(player, "highest_division", None)
        elif self.global_entry_division_basis == "last":
            return getattr(player, "last_division", None)
        elif self.global_entry_division_basis == "entry":
            return getattr(player, "entry_division", None)
        else:
            raise ValueError(f"Unknown global_entry_division_basis={self.global_entry_division_basis}")

    def _global_entry_basis_col(self) -> str:
        """
        Column name in players_total used to build yearly historical anchors.
        Assumes give_players_df stores these columns.
        """
        basis = getattr(self, "global_entry_division_basis", "highest").lower()
        if basis == "entry":
            return "Entry_Division"
        elif basis == "last":
            return "Last_Division"
        return "Highest_Division"


    def _global_entry_basis_divcode(self, series: pd.Series) -> pd.Series:
        """
        Convert division labels in players_total back to model division codes.
        players_total stores human-readable division names from _div_dict.
        """
        rev = {v: k for k, v in self._div_dict.items()}
        return series.map(rev)

    def _player_self_update_weight(self, player: Player_ADD) -> float:
        """
        Fixed self-damping:
        - established player -> 1.0
        - provisional player -> constant provisional_player_weight
        """
        if not getattr(player, "provisional", False):
            return 1.0
        return float(self.provisional_player_weight)


    def get_global_entry_cache(self) -> pd.DataFrame:
        rows = []

        for cache_year in sorted(self._global_entry_cache_history.keys()):
            cache = self._global_entry_cache_history.get(cache_year, {})
            counts = self._global_entry_count_history.get(cache_year, {})

            for div in sorted(cache.keys()):
                rows.append({
                    "cache_year": cache_year,
                    "division_code": div,
                    "division_name": self._div_dict.get(div, str(div)),
                    "entry_anchor": cache[div],
                    "contributors": counts.get(div, 0),
                    "basis": getattr(self, "global_entry_division_basis", "highest")
                })

        return pd.DataFrame(rows)

    def _append_tournament_snapshot_once(self, tourney: str, date):
        """
        Append exactly one full player snapshot per (Tournament, Date).
        Safe to call repeatedly.
        """
        date_ts = pd.Timestamp(date)

        if self.players_total.empty:
            self.players_total = pd.concat(
                [self.players_total, self.give_players_df(tourney, date)],
                ignore_index=True
            )
            return

        existing = self.players_total.copy()
        existing["Date"] = pd.to_datetime(existing["Date"], errors="coerce")

        already_logged = (
            (existing["Tournament"] == tourney) &
            (existing["Date"] == date_ts)
        ).any()

        if not already_logged:
            self.players_total = pd.concat(
                [self.players_total, self.give_players_df(tourney, date)],
                ignore_index=True
            )

    def _live_division_ratings_for_source_div(self, source_div: int) -> List[float]:
        """
        Current live ratings from self.p_dict for the mapped source division.
        Excludes provisional players by default.
        """
        ratings = []

        for p in self.p_dict.values():
            p_div = self._player_basis_div_code(p)
            if p_div != source_div:
                continue

            if self.blend_exclude_provisional and getattr(p, "provisional", False):
                continue

            ratings.append(float(p.rating))

        return ratings


    def _count_existing_players_in_field(self, player_array: List[str]) -> int:
        """
        Count existing players already in the system for the current tournament field.
        Excludes provisional players by default.
        """
        n = 0
        for name in player_array:
            if name not in self.p_dict:
                continue
            if self.blend_exclude_provisional and getattr(self.p_dict[name], "provisional", False):
                continue
            n += 1
        return n


    def _blended_live_division_starting_mu(self, div: int, player_array: List[str], baseline_mu: float) -> float:
        """
        Blend:
        - local tournament p33 among EXISTING players in this division/tournament
        - current GLOBAL live p33 of the mapped source division

        Rules:
        - If there are no live players globally in the mapped source division, use baseline_mu.
        - If there are no existing players in this tournament/division, use global_p33.
        - Otherwise blend local_tourney_p33 toward global_p33 based on the number of
            existing players in the field.

        Weight:
            w_local = min(blend_max_weight, n_existing / (n_existing + blend_existing_k))

        Final:
            start = w_local * local_tourney_p33 + (1 - w_local) * global_p33
        """
        # global comparison pool uses the mapped source division
        source_div = self.global_entry_source_map.get(int(div), int(div))
        global_live_ratings = self._live_division_ratings_for_source_div(source_div)

        # only use fixed baseline if there is no live global pool at all
        if len(global_live_ratings) == 0:
            return float(baseline_mu)

        global_p33 = float(np.percentile(global_live_ratings, 33))

        # local tournament pool = existing players already in the system in this field
        local_existing_ratings = []
        for name in player_array:
            if name not in self.p_dict:
                continue
            p = self.p_dict[name]
            if self.blend_exclude_provisional and getattr(p, "provisional", False):
                continue
            local_existing_ratings.append(float(p.rating))

        # if no existing players in the tournament field, default low to the current global p33
        if len(local_existing_ratings) == 0:
            return global_p33

        local_p33 = float(np.percentile(local_existing_ratings, 33))
        n_existing = len(local_existing_ratings)

        w_local = n_existing / (n_existing + self.blend_existing_k)
        w_local = min(self.blend_max_weight, w_local)

        return float(w_local * local_p33 + (1.0 - w_local) * global_p33)
    # -------------------------
    # Player/Team creation
    # -------------------------
    def create_teams(self, data: pd.DataFrame, tourney: str, division: str, date, avg_mu: bool = False):
        """
        Create or update players for `tourney`/`division`.

        Behavior:
        - Pre-cutoff years (<= fixed_entry_through_year): keep current fixed-baseline logic,
          optionally with local avg_mu if requested.
        - Post-cutoff years (> fixed_entry_through_year): if global_entry=True, use global
          division anchors refreshed every N years.
        - When global_entry=False, skip the new logic entirely and keep current behavior.
        """
        div = self._parse_division_code(division)
        baseline_mu = self._fixed_baseline_for_div(div)

        # select players appearing in this tourney/division
        filt_tab = data[(data["tourney"] == tourney) & (data["Division"] == division)]
        player_array = list(set(
            list(filt_tab["mT1P1"]) + list(filt_tab["mT1P2"]) +
            list(filt_tab["mT2P1"]) + list(filt_tab["mT2P2"])
        ))

        # choose entrant prior
        if self.blend_entry:
            starting_mu = self._blended_live_division_starting_mu(div, player_array, baseline_mu)
            
        elif self._should_use_global_entry_logic(date):
            starting_mu = self._global_starting_mu(div, date)
        else:
            starting_mu = baseline_mu
            if avg_mu:
                starting_mu = self._legacy_local_starting_mu(player_array, baseline_mu)
                # create or update players

        for player in player_array:
            if player not in self.p_dict:
                self.p_dict[player] = Player_ADD(
                    name=player,
                    starting_rating=starting_mu,
                    starting_rd=self.entry_rd,
                    starting_sigma=0.06,
                    glicko_scale=self.GLICKO_SCALE,
                    tau=self.tau,
                    time_constant=self.time_constant,
                    convexity=self.convexity,
                    rd_min=self.rd_min,
                    rd_max=self.rd_max,
                    cap_redux=self.cap_redux,
                    max_reduction_frac=self.max_reduction_frac,
                    rd_inflation_mode=self.rd_inflation_mode,
                    buffer_days=self.buffer_days,
                    decay_tau_days=self.decay_tau_days,
                    sat_power=self.sat_power,
                    provisional=self.provisional_flag,
                    provisional_min_tournaments=self.provisional_min_tournaments,
                    provisional_min_games=self.provisional_min_games,
                    cap_provisional_update=self.cap_provisional_update,
                    provisional_cap_first_gain_elo=self.provisional_cap_first_gain_elo,
                    provisional_cap_second_gain_elo=self.provisional_cap_second_gain_elo,
                )
                self.p_dict[player].add_tourney(tourney)
                self.p_dict[player].add_division(div)
                self.p_dict[player].update_time(date)
            else:
                self.p_dict[player].add_tourney(tourney)
                self.p_dict[player].add_division(div)

                self.p_dict[player].update_days_last_played(date)
                self.p_dict[player].update_rd()
                self.p_dict[player].update_time(date)


    def _player_basis_div_code(self, player: Player_ADD) -> Optional[int]:
        """
        Match the division-basis logic used for global entry, but on live players.
        """
        basis = str(getattr(self, "global_entry_division_basis", "entry")).lower()

        if basis == "highest":
            return getattr(player, "highest_division", None)
        elif basis == "last":
            return getattr(player, "last_division", None)
        else:
            return getattr(player, "entry_division", None)




    # -------------------------
    # read_games (filter)
    # -------------------------
    def read_games(self, data: pd.DataFrame, tourney: str, division: str = "PREMIER"):
        d = data[(data["tourney"] == tourney) & (data["Division"] == division)].dropna(subset=["mT1_result"]).reset_index(drop=True)
        d = d[(d["mT1_result"] != 0.5)].reset_index(drop=True)
        self.temp_games = d

    # -------------------------
    # Core: record_game
    # -------------------------
    def record_game(self, player1: str, player2: str, player3: str, player4: str, winner: int, index: int):
        # ensure players exist
        for p in (player1, player2, player3, player4):
            if p not in self.p_dict:
                print(p)
                self.p_dict[p] = Player_ADD(
                    name=p,
                    starting_rating=self.sep,
                    starting_rd=self.rd_max,
                    glicko_scale=self.GLICKO_SCALE,
                    tau=self.tau,
                    time_constant=self.time_constant,
                    convexity=self.convexity,
                    rd_min=self.rd_min,
                    rd_max=self.rd_max,
                    cap_redux=self.cap_redux,
                    max_reduction_frac=self.max_reduction_frac,
                    rd_inflation_mode=self.rd_inflation_mode,
                    buffer_days=self.buffer_days,
                    decay_tau_days=self.decay_tau_days,
                    sat_power=self.sat_power,
                    provisional=self.provisional_flag
                )
        p1 = self.p_dict[player1]
        p2 = self.p_dict[player2]
        p3 = self.p_dict[player3]
        p4 = self.p_dict[player4]
        players = [p1, p2, p3, p4]

        # --- Logging: Avg Elo & Min Games (unchanged from your logic) ---
        avg_rating = sum(p.rating for p in players) / 4
        min_games = min(p.games for p in players)

        # logging
        try:
            self.temp_games.at[index, "T1P1 ELO"] = p1.rating
            self.temp_games.at[index, "T1P2 ELO"] = p2.rating
            self.temp_games.at[index, "T2P1 ELO"] = p3.rating
            self.temp_games.at[index, "T2P2 ELO"] = p4.rating
            self.temp_games.at[index, "T1P1 RD"] = p1.RD
            self.temp_games.at[index, "T1P2 RD"] = p2.RD
            self.temp_games.at[index, "T2P1 RD"] = p3.RD
            self.temp_games.at[index, "T2P2 RD"] = p4.RD
            self.temp_games.at[index, "Avg Elo"] = avg_rating
            self.temp_games.at[index, "Min Games"] = min_games
        except Exception:
            pass

        # compute team stats according to selected method
        team1_mu, team1_phi = self._team_stats([p1, p2])
        team2_mu, team2_phi = self._team_stats([p3, p4])

        #compute team reliablity
        team1_rel = self._team_reliability([p1, p2])
        team2_rel = self._team_reliability([p3, p4])

        # Compute self weigth for provisional
        p1_self_w = self._player_self_update_weight(p1)
        p2_self_w = self._player_self_update_weight(p2)
        p3_self_w = self._player_self_update_weight(p3)
        p4_self_w = self._player_self_update_weight(p4)

        # team-level probability (for logging)
        prob_team1 = E(team1_mu, team2_mu, team2_phi)
        prob_team2 = 1.0 - prob_team1
        try:
            self.temp_games.at[index, "prob"] = prob_team2
        except Exception:
            pass

        # per-player E vs opponent team (player mu vs opponent team mu/phi)
        g_team2 = g(team2_phi)
        g_team1 = g(team1_phi)

        E_p1 = E(p1.mu, team2_mu, team2_phi)
        E_p2 = E(p2.mu, team2_mu, team2_phi)
        E_p3 = E(p3.mu, team1_mu, team1_phi)
        E_p4 = E(p4.mu, team1_mu, team1_phi)


        # per-player v (single match inverse variance), discounted by opponent-team reliability
        v_inv_p1 = p1_self_w * team2_rel * (g_team2 ** 2) * E_p1 * (1.0 - E_p1)
        v_inv_p2 = p2_self_w * team2_rel * (g_team2 ** 2) * E_p2 * (1.0 - E_p2)
        v_inv_p3 = p3_self_w * team1_rel * (g_team1 ** 2) * E_p3 * (1.0 - E_p3)
        v_inv_p4 = p4_self_w * team1_rel * (g_team1 ** 2) * E_p4 * (1.0 - E_p4)

        v_p1 = 1.0 / max(v_inv_p1, 1e-12)
        v_p2 = 1.0 / max(v_inv_p2, 1e-12)
        v_p3 = 1.0 / max(v_inv_p3, 1e-12)
        v_p4 = 1.0 / max(v_inv_p4, 1e-12)

        # scores
        team1_score = 1 if winner == 1 else 0
        team2_score = 1 - team1_score

        # per-player delta (g * (s - E_player))
        delta_p1 = p1_self_w * team2_rel * g_team2 * (team1_score - E_p1)
        delta_p2 = p2_self_w * team2_rel * g_team2 * (team1_score - E_p2)
        delta_p3 = p3_self_w * team1_rel * g_team1 * (team2_score - E_p3)
        delta_p4 = p4_self_w * team1_rel * g_team1 * (team2_score - E_p4)

        # store per-player evidence
        p1.add_team_result(delta_p1, g_team2, E_p1, v_p1)
        p2.add_team_result(delta_p2, g_team2, E_p2, v_p2)
        p3.add_team_result(delta_p3, g_team1, E_p3, v_p3)
        p4.add_team_result(delta_p4, g_team1, E_p4, v_p4)

        # legacy-style expected deltas for logging (approx)
        p1_expected = expected_match_delta(p1.mu, p1.phi, team2_phi, team1_score, prob_team1)
        p2_expected = expected_match_delta(p2.mu, p2.phi, team2_phi, team1_score, prob_team1)
        p3_expected = expected_match_delta(p3.mu, p3.phi, team1_phi, team2_score, prob_team2)
        p4_expected = expected_match_delta(p4.mu, p4.phi, team1_phi, team2_score, prob_team2)

        # write to temp_games for compatibility
        try:
            self.temp_games.at[index, "T1P1 Change"] = p1_expected * self.GLICKO_SCALE
            self.temp_games.at[index, "T1P2 Change"] = p2_expected * self.GLICKO_SCALE
            self.temp_games.at[index, "T2P1 Change"] = p3_expected * self.GLICKO_SCALE
            self.temp_games.at[index, "T2P2 Change"] = p4_expected * self.GLICKO_SCALE
        except Exception:
            pass

        # store team-level result for bookkeeping
        try:
            self.temp_games.at[index, "Win"] = (winner != 1)
        except Exception:
            pass

        if self.instant_update:
            p1.update_player(self.temp_games.at[index, "Date"])
            p2.update_player(self.temp_games.at[index, "Date"])
            p3.update_player(self.temp_games.at[index, "Date"])
            p4.update_player(self.temp_games.at[index, "Date"])

    # -------------------------
    # record_tourney (plays the tournament and updates players)
    # -------------------------
    def record_tourney(self, data: pd.DataFrame, tourney: str, division: str, date, avg_mu: bool = False):
        self.create_teams(data, tourney, division, date, avg_mu)
        self.read_games(data, tourney, division)

       # preferred explicit dtypes for columns we use
        cols_bool = ["Win"]
        cols_float = [
        "T1P1 Change", "T1P2 Change", "T2P1 Change", "T2P2 Change",
        "T1P1 ELO", "T1P2 ELO", "T2P1 ELO", "T2P2 ELO",
        "T1P1 RD", "T1P2 RD", "T2P1 RD", "T2P2 RD", "Min Games", "Avg Elo", "prob"
        ]

        for c in cols_float:
            if c not in self.temp_games.columns:
                self.temp_games[c] = 0.0
            else:
                # coerce dtype to float
                self.temp_games[c] = self.temp_games[c].astype(float)

        for c in cols_bool:
            if c not in self.temp_games.columns:
                self.temp_games[c] = pd.Series([False] * len(self.temp_games), dtype=bool)
            else:
                self.temp_games[c] = self.temp_games[c].astype(bool)

        # iterate matches
        for index, row in self.temp_games.iterrows():
            self.record_game(row["mT1P1"], row["mT1P2"], row["mT2P1"], row["mT2P2"], row["mT1_result"], index)

        # append to played_games
        self.played_games = pd.concat([self.played_games, self.temp_games], ignore_index=True)

        # update all players at end-of-tourney
        for player in self.p_dict.values():
            player.update_player(date)

        # store players snapshot for this tournament (compatibility)
        try:
            self.players_total = pd.concat([self.players_total, self.give_players_df(tourney, date)], ignore_index=True)
        except Exception:
            pass

        # remove inactive players if requested
        if self.remove:
            for name in list(self.p_dict.keys()):
                if self.p_dict[name].days_since_played > self.remove_time:
                    del self.p_dict[name]

    # -------------------------
    # record_season (multiple tourns)
    # -------------------------
    def record_season(self, data: pd.DataFrame, combos: pd.DataFrame):
        orders = combos["order"].unique()
        for j in orders:
            combos_t = combos[combos["order"] == j].reset_index(drop=True)
            for i in range(len(combos_t)):
                row = combos_t.loc[i]
                if not self.avg_mu:
                    avg_mu_flag = False
                else:
                    avg_mu_flag = bool(row.get("AVG_ELO", False))
                self.record_tourney(data, row["tourney"], row["Division"], row["Date"], avg_mu=avg_mu_flag)
            # update players (already done in record_tourney but keep for safety)
            for p in self.p_dict.values():
                p.update_player(combos_t.loc[i, "Date"])

            # cleanup players_total appended in record_tourney

    # -------------------------
    # prediction helpers (mirror original)
    # -------------------------
    def predict_game(self, player1: str, player2: str, player3: str, player4: str, winner: int, index: int):
        # pull players
        p1 = self.p_dict[player1]
        p2 = self.p_dict[player2]
        p3 = self.p_dict[player3]
        p4 = self.p_dict[player4]

        # compute team-level Elo average for compatibility with previous code
        elo1 = (p1.rating + p2.rating) / 2.0
        elo2 = (p3.rating + p4.rating) / 2.0
        cutoff = calculate_win_prob(elo1, elo2)

        pred_win = None
        if cutoff < 0.5:
            pred_win = 1
        elif cutoff > 0.5:
            pred_win = 0
        else:
            pred_win = None
            try:
                self.temp_games.at[index, "Predict_win"] = 0.5
            except Exception:
                pass

        if winner == 1:
            if pred_win == 0 and cutoff != 0.5:
                try:
                    self.temp_games.at[index, "Predict_win"] = 1
                except Exception:
                    pass
            try:
                self.temp_games.at[index, "Win"] = False
            except Exception:
                pass
        else:
            if pred_win == 0 and cutoff != 0.5:
                try:
                    self.temp_games.at[index, "Predict_win"] = 1
                except Exception:
                    pass
            try:
                self.temp_games.at[index, "Win"] = True
            except Exception:
                pass

        try:
            self.temp_games.at[index, "prob"] = cutoff
            self.temp_games.at[index, "Avg Elo"] = (p1.rating + p2.rating + p3.rating + p4.rating) / 4.0
            self.temp_games.at[index, "Min Games"] = min(p1.games, p2.games, p3.games, p4.games)
        except Exception:
            pass


    def record_tourney_fast(self, data: pd.DataFrame, tourney: str, division: str, date, avg_mu: bool = False):
        """Faster version of record_tourney: buffers per-row writes and uses itertuples().
        Keeps the same per-player math and calls to Player_ADD.add_team_result/update_player.
        """
        # prepare players & games (same semantics as original)
        self.create_teams(data, tourney, division, date, avg_mu)
        self.read_games(data, tourney, division)
        n = len(self.temp_games)
        if n == 0:
            return

        # Ensure columns exist and have correct dtypes (avoid try/except in hot loop)
        float_cols = ["T1P1 Change","T1P2 Change","T2P1 Change","T2P2 Change",
                    "T1P1 ELO","T1P2 ELO","T2P1 ELO","T2P2 ELO",
                    "T1P1 RD","T1P2 RD","T2P1 RD","T2P2 RD","Min Games","Avg Elo","prob"]
        bool_cols = ["Win"]
        for c in float_cols:
            if c not in self.temp_games.columns:
                self.temp_games[c] = 0.0
            else:
                self.temp_games[c] = self.temp_games[c].astype(float)
        for c in bool_cols:
            if c not in self.temp_games.columns:
                self.temp_games[c] = pd.Series([False]*n, dtype=bool)
            else:
                self.temp_games[c] = self.temp_games[c].astype(bool)

        # Pre-allocate buffers (lists) for column values
        buf = {c: [None]*n for c in (float_cols + bool_cols + ["Predict_win"])}

        # Local references to avoid repeated attribute lookups
        p_dict = self.p_dict
        g_fn = g
        E_fn = E
        expected_fn = expected_match_delta
        GLICKO_SCALE = self.GLICKO_SCALE
        team_stats = self._team_stats
        team_reliability = self._team_reliability

        # Fast iteration
        # itertuples(index=True) would return index as first field; use itertuples(index=False) for positional fields
        # But to be robust to column order, access the named attributes expected to exist in your DataFrame.
        for idx, row in enumerate(self.temp_games.itertuples(index=False)):
            # retrieve required fields by name (these must exist in temp_games)
            p1_name = getattr(row, "mT1P1")
            p2_name = getattr(row, "mT1P2")
            p3_name = getattr(row, "mT2P1")
            p4_name = getattr(row, "mT2P2")
            winner = getattr(row, "mT1_result")
            # Date may or may not be present in the tuple; fallback to provided date
            current_date = getattr(row, "Date", date)

            # Ensure players exist (same semantics as record_game)
            for name in (p1_name, p2_name, p3_name, p4_name):
                if name not in p_dict:
                    print(name)
                    p_dict[name] = Player_ADD(
                        name=name,
                        starting_rating=self.sep,
                        starting_rd=self.rd_max,
                        glicko_scale=self.GLICKO_SCALE,
                        tau=self.tau,
                        time_constant=self.time_constant,
                        convexity=self.convexity,
                        rd_min=self.rd_min,
                        rd_max=self.rd_max
                    )

            p1 = p_dict[p1_name]; p2 = p_dict[p2_name]; p3 = p_dict[p3_name]; p4 = p_dict[p4_name]

            # quick derived values
            avg_rating = (p1.rating + p2.rating + p3.rating + p4.rating) / 4.0
            min_games = min(p1.games, p2.games, p3.games, p4.games)

            # team stats and probabilities (same as original)
            team1_mu, team1_phi = team_stats([p1, p2])
            team2_mu, team2_phi = team_stats([p3, p4])

            team1_rel = team_reliability([p1, p2])
            team2_rel = team_reliability([p3, p4])

            p1_self_w = self._player_self_update_weight(p1)
            p2_self_w = self._player_self_update_weight(p2)
            p3_self_w = self._player_self_update_weight(p3)
            p4_self_w = self._player_self_update_weight(p4)
            
            prob_team1 = E_fn(team1_mu, team2_mu, team2_phi)
            prob_team2 = 1.0 - prob_team1

            g_team2 = g_fn(team2_phi); g_team1 = g_fn(team1_phi)
            E_p1 = E_fn(p1.mu, team2_mu, team2_phi)
            E_p2 = E_fn(p2.mu, team2_mu, team2_phi)
            E_p3 = E_fn(p3.mu, team1_mu, team1_phi)
            E_p4 = E_fn(p4.mu, team1_mu, team1_phi)

            v_p1 = 1.0 / max(p1_self_w * team2_rel * (g_team2**2) * E_p1 * (1.0 - E_p1), 1e-12)
            v_p2 = 1.0 / max(p2_self_w * team2_rel * (g_team2**2) * E_p2 * (1.0 - E_p2), 1e-12)
            v_p3 = 1.0 / max(p3_self_w * team1_rel * (g_team1**2) * E_p3 * (1.0 - E_p3), 1e-12)
            v_p4 = 1.0 / max(p4_self_w * team1_rel * (g_team1**2) * E_p4 * (1.0 - E_p4), 1e-12)

            # scores and deltas
            team1_score = 1 if winner == 1 else 0
            team2_score = 1 - team1_score

            delta_p1 = p1_self_w * team2_rel * g_team2 * (team1_score - E_p1)
            delta_p2 = p2_self_w * team2_rel * g_team2 * (team1_score - E_p2)
            delta_p3 = p3_self_w * team1_rel * g_team1 * (team2_score - E_p3)
            delta_p4 = p4_self_w * team1_rel * g_team1 * (team2_score - E_p4)

            # store per-player evidence (unchanged logic)
            p1.add_team_result(delta_p1, g_team2, E_p1, v_p1)
            p2.add_team_result(delta_p2, g_team2, E_p2, v_p2)
            p3.add_team_result(delta_p3, g_team1, E_p3, v_p3)
            p4.add_team_result(delta_p4, g_team1, E_p4, v_p4)

            # legacy expected deltas for logging
            p1_expected = expected_fn(p1.mu, p1.phi, team2_phi, team1_score, prob_team1)
            p2_expected = expected_fn(p2.mu, p2.phi, team2_phi, team1_score, prob_team1)
            p3_expected = expected_fn(p3.mu, p3.phi, team1_phi, team2_score, prob_team2)
            p4_expected = expected_fn(p4.mu, p4.phi, team1_phi, team2_score, prob_team2)

            # buffer all values (assign once at end)
            buf["T1P1 Change"][idx] = p1_expected * GLICKO_SCALE
            buf["T1P2 Change"][idx] = p2_expected * GLICKO_SCALE
            buf["T2P1 Change"][idx] = p3_expected * GLICKO_SCALE
            buf["T2P2 Change"][idx] = p4_expected * GLICKO_SCALE

            buf["T1P1 ELO"][idx] = p1.rating
            buf["T1P2 ELO"][idx] = p2.rating
            buf["T2P1 ELO"][idx] = p3.rating
            buf["T2P2 ELO"][idx] = p4.rating

            buf["T1P1 RD"][idx] = p1.RD
            buf["T1P2 RD"][idx] = p2.RD
            buf["T2P1 RD"][idx] = p3.RD
            buf["T2P2 RD"][idx] = p4.RD

            buf["Avg Elo"][idx] = avg_rating
            buf["Min Games"][idx] = min_games
            buf["prob"][idx] = prob_team2
            buf["Win"][idx] = (winner != 1)
            buf["Predict_win"][idx] = None

            # instant_update preserved (if set)
            if self.instant_update:
                p1.update_player(current_date)
                p2.update_player(current_date)
                p3.update_player(current_date)
                p4.update_player(current_date)

        # Single DataFrame assignment for each buffered column
        for col, arr in buf.items():
            self.temp_games[col] = arr

        # append to played_games and update players (same as original)
        self.played_games = pd.concat([self.played_games, self.temp_games], ignore_index=True)

        for player in self.p_dict.values():
            player.update_player(date)


        

        if self.remove:
            for name in list(self.p_dict.keys()):
                if self.p_dict[name].days_since_played > self.remove_time:
                    del self.p_dict[name]

      


    def record_season_fast(self, data: pd.DataFrame, combos: pd.DataFrame):
        """Call record_tourney_fast in the same order as record_season to preserve behavior."""
        orders = combos["order"].unique()
        for j in orders:
            combos_t = combos[combos["order"] == j].reset_index(drop=True)
            for i in range(len(combos_t)):
                row = combos_t.loc[i]
                if not self.avg_mu:
                    avg_mu_flag = False
                else:
                    avg_mu_flag = bool(row.get("AVG_ELO", False))

                self.record_tourney_fast(data, row["tourney"], row["Division"], row["Date"], avg_mu=avg_mu_flag)

                # after the last division row for a tournament/date block, save one snapshot
                is_last_row = (i == len(combos_t) - 1)
                if not is_last_row:
                    next_row = combos_t.loc[i + 1]
                    same_block = (
                        (next_row["tourney"] == row["tourney"]) and
                        (pd.Timestamp(next_row["Date"]) == pd.Timestamp(row["Date"]))
                    )
                else:
                    same_block = False

                if not same_block:
                    self._append_tournament_snapshot_once(row["tourney"], row["Date"])

    def predict_tourney(self, data: pd.DataFrame, tourney: str, division: str):
        self.create_teams(data, tourney, division, date=pd.Timestamp.now())
        self.read_games(data, tourney, division)
        self.temp_games["prob"] = 0.0
        self.temp_games["Win"] = True
        self.temp_games["Min Games"] = 0
        self.temp_games["Avg Elo"] = 0.0
        self.temp_games["Predict_win"] = 0.0
        for index, row in self.temp_games.iterrows():
            self.predict_game(row["mT1P1"], row["mT1P2"], row["mT2P1"], row["mT2P2"], row["mT1_result"], index)
        self.predicted_games = pd.concat([self.predicted_games, self.temp_games], ignore_index=True)

    def predict_season(self, data: pd.DataFrame, combos: pd.DataFrame):
        for i in range(len(combos)):
            self.predict_tourney(data, combos.loc[i, "tourney"], combos.loc[i, "Division"])
        if not self.predicted_games.empty:
            self.predicted_games = self.predicted_games.dropna(subset=['Predict_win']).reset_index(drop=True)

    # -------------------------
    # diagnostics and utility
    # -------------------------
    def brier_score(self, mg: int):
        games = self.played_games.loc[self.played_games["Min Games"] >= mg]
        if len(games) == 0:
            return None
        return float(((games["prob"] - games["Win"].astype(int)) ** 2).mean())

    def give_players_df(self, tourney: Optional[str] = None, date: Optional[Any] = None) -> pd.DataFrame:
        data = []
        for player_name, player_obj in self.p_dict.items():
            highest_div = getattr(player_obj, "highest_division", None)
            entry_div = getattr(player_obj, "entry_division", None)
            last_div = getattr(player_obj, "last_division", None)

            data.append([
            player_obj.name,
            player_obj.rating,
            getattr(player_obj, "entry_rating", np.nan),
            player_obj.RD,
            player_obj.games,
            len(player_obj.tournies),
            player_obj.days_since_played,
            self._div_dict.get(highest_div, highest_div),
            self._div_dict.get(entry_div, entry_div),
            self._div_dict.get(last_div, last_div),
        ])

        df = pd.DataFrame(
            data,
            columns=[
                'name', 'rating', 'entry_rating', "RD", 'game', 'tournies', 'days_since_played',
                "Highest_Division", "Entry_Division", "Last_Division"
            ]
        )
        df = df.sort_values(by='rating', ascending=False).reset_index(drop=True)

        if tourney is not None and date is not None:
            df["Date"] = [date] * len(df)
            df["Tournament"] = [tourney] * len(df)

        df = df.rename(columns={'game': 'Games_Played', 'tournies': 'Tournaments_Played'})
        return df


    def give_players_all(self) -> pd.DataFrame:
        return self.players_total.reset_index(drop=True) if not self.players_total.empty else pd.DataFrame()

    def model_diagnostics(self, min_games: int = 5):
        games = self.played_games.loc[self.played_games["Min Games"] >= min_games].copy()
        if len(games) == 0:
            return None
        p = games["prob"].astype(float).clip(1e-6, 1 - 1e-6)
        y = games["Win"].astype(int)
        brier = ((p - y) ** 2).mean()
        log_loss = -(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()
        X = np.vstack([np.ones(len(p)), p]).T
        beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        calib_intercept, calib_slope = beta
        expected_winrate = p.mean()
        observed_winrate = y.mean()
        prob_variance = p.var()
        confident_frac = ((p < 0.2) | (p > 0.8)).mean()
        upset_mask = (p >= 0.35) & (p <= 0.65)
        upset_accuracy = ((p[upset_mask] > 0.5) == y[upset_mask]).mean() if upset_mask.sum() > 0 else np.nan
        rd_values = self.players_total["RD"].dropna() if not self.players_total.empty else pd.Series([])
        rd_mean = float(rd_values.mean()) if not rd_values.empty else np.nan
        rd_median = float(rd_values.median()) if not rd_values.empty else np.nan
        rd_p90 = float(rd_values.quantile(0.9)) if not rd_values.empty else np.nan
        return {
            "brier": float(brier),
            "log_loss": float(log_loss),
            "calibration_slope": float(calib_slope),
            "calibration_intercept": float(calib_intercept),
            "expected_winrate": float(expected_winrate),
            "observed_winrate": float(observed_winrate),
            "prob_variance": float(prob_variance),
            "confident_fraction": float(confident_frac),
            "upset_accuracy": float(upset_accuracy),
            "rd_mean": rd_mean,
            "rd_median": rd_median,
            "rd_p90": rd_p90,
            "num_games": len(games),
        }
    def entrant_spike_metrics(
    self,
    gain_threshold: float = 100.0,
    max_tournaments: int = 1,
    ) -> Optional[Dict[str, float]]:
        """
        Diagnostics for entrant overshoot.

        Uses the earliest snapshot for each player among players with
        Tournaments_Played <= max_tournaments, then measures:
        - rating gain vs entry_rating
        - distribution summaries
        - fraction above a large-gain threshold

        This is for tracking/diagnostics only, not model selection.
        """
        if not hasattr(self, "players_total") or self.players_total is None or self.players_total.empty:
            return None

        df = self.players_total.copy()

        required = {"name", "rating", "entry_rating", "Tournaments_Played"}
        if not required.issubset(df.columns):
            return None

        # make sure we can identify the earliest eligible snapshot per player
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            sort_cols = ["name", "Date", "Tournaments_Played", "rating"]
        else:
            sort_cols = ["name", "Tournaments_Played", "rating"]

        df = df.loc[df["Tournaments_Played"] <= max_tournaments].copy()
        if df.empty:
            return None

        df = df.sort_values(sort_cols).drop_duplicates(subset=["name"], keep="first")

        df["entry_gain"] = pd.to_numeric(df["rating"], errors="coerce") - pd.to_numeric(df["entry_rating"], errors="coerce")
        gains = df["entry_gain"].replace([np.inf, -np.inf], np.nan).dropna()

        if gains.empty:
            return None

        return {
            "entrant_n": int(len(gains)),
            "entrant_gain_mean": float(gains.mean()),
            "entrant_gain_median": float(gains.median()),
            "entrant_gain_p75": float(gains.quantile(0.75)),
            "entrant_gain_p90": float(gains.quantile(0.90)),
            "entrant_gain_p95": float(gains.quantile(0.95)),
            "entrant_gain_max": float(gains.max()),
            "entrant_frac_gt_thresh": float((gains > gain_threshold).mean()),
        }

    def trace_player(self, name: str):
        if name not in self.p_dict:
            print(f"{name} not in p_dict")
            return

        p = self.p_dict[name]
        print("name:", p.name)
        print("current_rating:", p.rating)
        print("entry_rating:", p.entry_rating)
        print("games:", p.games)
        print("tournaments:", p.tournies)
        print("entry_division:", p.entry_division)
        print("last_division:", p.last_division)
        print("highest_division:", p.highest_division)

        if not self.players_total.empty:
            df = self.players_total[self.players_total["name"] == name].copy()
            if not df.empty:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                print(df.sort_values("Date")[["Date", "Tournament", "rating", "entry_rating",
                                            "Games_Played", "Tournaments_Played",
                                            "Entry_Division", "Last_Division",
                                            "Highest_Division"]].head(10))