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
        max_reduction_frac: float =0.15,
        cap_redux=False,
        rd_inflation_mode: str = "power",   # "power" (default) | "saturating"
        buffer_days: float = 0.0,           # grace period before inflating RD
        decay_tau_days: float = 90.0,       # saturating time constant (days)
        sat_power: float = 1.0              # optional shape: <1 more concave after buffer
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
        self._team_results: List[Tuple[float, float, float, float]] = []  # (delta, g_op, E, v)
        self.highest_division = 10
        self.games = games
        self.tournies: List[str] = []
        self.days_since_played = time_since_play
        self.last_played = None
        self.phi_last = self.phi
        self.max_reduction_frac = max_reduction_frac
        self.cap_redux= cap_redux
        self.rd_inflation_mode = rd_inflation_mode
        self.buffer_days = float(buffer_days)
        self.decay_tau_days = float(decay_tau_days)
        self.sat_power = float(sat_power)
        

    @property
    def rating(self) -> float:
        """Return Elo-scale rating for external display."""
        return 1500.0 + self.mu * self.glicko_scale

    @property
    def RD(self) -> float:
        """Return Elo-scale RD for external display."""
        return self.phi * self.glicko_scale

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

        # Step 1: accumulate v_inv & delta_sum
        v_inv = 0.0
        delta_sum = 0.0
        for delta, g_op, E_val, v in self._team_results:
            v_inv += (g_op ** 2) * E_val * (1.0 - E_val)
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


        # cleanup & housekeeping
        self._team_results = []
        self.phi = max(self.phi_min, self.phi)
        self.phi_last = self.phi
        self.update_time(date)
        
        

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
        sat_power: float = 1.0
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
        # sanity
        assert team_method in ('sum', 'avg', 'inv_var')
        self.rd_inflation_mode = rd_inflation_mode
        self.buffer_days = float(buffer_days)
        self.decay_tau_days = float(decay_tau_days)
        self.sat_power = float(sat_power)

        assert self.rd_inflation_mode in ("power", "convexity", "saturating", "sat")

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

    # -------------------------
    # Player/Team creation (mirrors your original create_teams)
    # -------------------------
    def create_teams(self, data: pd.DataFrame, tourney: str, division: str, date, avg_mu: bool = False):
        """
        Create or update players for `tourney`/`division`.

        avg_mu: False | True | "mean" | "pct33"
          - False: use division baseline (sep, sep-de, sep-dc)
          - True: use division median of existing players (back-compat)
          - "mean": use division mean of existing players
          - "pct33": use 33rd percentile of existing players
        Behavior: If fewer than self.min_existing_for_stat existing players are present
        in the division, default to the division baseline (sep +/- de/dc).
        """
        # map division string to integer div (0..3) and baseline starting_mu
        if ("PREMIER" in division) or ("PRO" in division):
            div = 1
            if "PRO" in division:
                div = 0
            baseline_mu = self.sep
        elif any(x in division for x in ["EXPERT", "ELITE", "GOLD", "WOMEN"]):
            div = 2
            baseline_mu = self.sep - self.de
        else:
            div = 3
            baseline_mu = self.sep - self.dc

        # select players appearing in this tourney/division
        filt_tab = data[(data["tourney"] == tourney) & (data["Division"] == division)]
        player_array = list(set(
            list(filt_tab["mT1P1"]) + list(filt_tab["mT1P2"]) +
            list(filt_tab["mT2P1"]) + list(filt_tab["mT2P2"])
        ))

        # decide division-level starting_mu from existing players if requested
        starting_mu = baseline_mu
        if avg_mu:
            # collect existing players that are already in p_dict and appear in this tourney/division
            existing_mus = []
            for p in player_array:
                if p in self.p_dict:
                    # convert internal mu back to Elo-scale for compatibility with sep/de/dc
                    existing_mus.append(self.p_dict[p].mu * self.GLICKO_SCALE + 1500.0)

            # only use the statistic if enough existing players are present
            if len(existing_mus) >= max(1, int(self.min_existing_for_stat)):
                if self.avg_mode == "mean":
                    starting_mu = float(np.mean(existing_mus))
                elif self.avg_mode in ("pct33", "p33", "33"):
                    starting_mu = float(np.percentile(existing_mus, 33))
                elif self.avg_mode in ("median", "50", "pct50"):
                    starting_mu = float(np.percentile(existing_mus, 50))
                else:
                    starting_mu = float(np.percentile(existing_mus, 50))
            else:
                # not enough existing players -> fallback to baseline (sep - de/dc)
                starting_mu = baseline_mu

        # create or update players
        for player in player_array:
            if player not in self.p_dict:
                self.p_dict[player] = Player_ADD(
                    name=player,
                    starting_rating=starting_mu,
                    starting_rd=self.rd_max,  # start with max RD to be conservative
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
                    sat_power=self.sat_power
                )
                self.p_dict[player].add_tourney(tourney)
                self.p_dict[player].add_division(div)
                self.p_dict[player].update_time(date)
            else:
                # existing player: update meta and conservative aging
                self.p_dict[player].add_tourney(tourney)
                self.p_dict[player].add_division(div)

                # 1) compute days since last play using previous last_played
                self.p_dict[player].update_days_last_played(date)

                # 2) inflate RD based on that gap BEFORE any matches are processed
                self.p_dict[player].update_rd()

                # 3) now set last_played = date for bookkeeping (do not recompute days here)
                self.p_dict[player].update_time(date)
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

        # per-player v (single match inverse variance)
        v_inv_p1 = (g_team2 ** 2) * E_p1 * (1.0 - E_p1)
        v_inv_p2 = (g_team2 ** 2) * E_p2 * (1.0 - E_p2)
        v_inv_p3 = (g_team1 ** 2) * E_p3 * (1.0 - E_p3)
        v_inv_p4 = (g_team1 ** 2) * E_p4 * (1.0 - E_p4)

        v_p1 = 1.0 / max(v_inv_p1, 1e-12)
        v_p2 = 1.0 / max(v_inv_p2, 1e-12)
        v_p3 = 1.0 / max(v_inv_p3, 1e-12)
        v_p4 = 1.0 / max(v_inv_p4, 1e-12)

        # scores
        team1_score = 1 if winner == 1 else 0
        team2_score = 1 - team1_score

        # per-player delta (g * (s - E_player))
        delta_p1 = g_team2 * (team1_score - E_p1)
        delta_p2 = g_team2 * (team1_score - E_p2)
        delta_p3 = g_team1 * (team2_score - E_p3)
        delta_p4 = g_team1 * (team2_score - E_p4)

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
            prob_team1 = E_fn(team1_mu, team2_mu, team2_phi)
            prob_team2 = 1.0 - prob_team1

            g_team2 = g_fn(team2_phi); g_team1 = g_fn(team1_phi)
            E_p1 = E_fn(p1.mu, team2_mu, team2_phi)
            E_p2 = E_fn(p2.mu, team2_mu, team2_phi)
            E_p3 = E_fn(p3.mu, team1_mu, team1_phi)
            E_p4 = E_fn(p4.mu, team1_mu, team1_phi)

            v_p1 = 1.0 / max((g_team2**2)*E_p1*(1.0 - E_p1), 1e-12)
            v_p2 = 1.0 / max((g_team2**2)*E_p2*(1.0 - E_p2), 1e-12)
            v_p3 = 1.0 / max((g_team1**2)*E_p3*(1.0 - E_p3), 1e-12)
            v_p4 = 1.0 / max((g_team1**2)*E_p4*(1.0 - E_p4), 1e-12)

            # scores and deltas
            team1_score = 1 if winner == 1 else 0
            team2_score = 1 - team1_score

            delta_p1 = g_team2 * (team1_score - E_p1)
            delta_p2 = g_team2 * (team1_score - E_p2)
            delta_p3 = g_team1 * (team2_score - E_p3)
            delta_p4 = g_team1 * (team2_score - E_p4)

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
            # Final per-order player update (matching original semantics)
            for p in self.p_dict.values():
                p.update_player(combos_t.loc[i, "Date"])
            try:
                self.players_total = pd.concat([self.players_total, self.give_players_df(combos_t.loc[i, "tourney"], combos_t.loc[i, "Date"])], ignore_index=True)
            except Exception:
                pass

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
            data.append([player_obj.name, player_obj.rating, player_obj.RD, player_obj.games, len(player_obj.tournies), player_obj.days_since_played, self._div_dict[player_obj.highest_division]])
        df = pd.DataFrame(data, columns=['name', 'rating', "RD", 'game', 'tournies', 'days_since_played', "Highest_Division"])
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