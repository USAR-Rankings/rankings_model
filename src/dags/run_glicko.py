import pandas as pd
import random as random
from itertools import chain
import warnings
warnings.filterwarnings(action='once')
from datetime import date,datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
print(os.getcwd())  # Check the current working directory
from src.tasks.run_glicko.core import *
#from ..tasks.run_elo.core import *
#from ..tasks.run_elo.helpers import *
from src.configs.run_glicko_both import (OPEN_P,WOMENS_P)

def main():
    params =[OPEN_P,WOMENS_P]  
    for param in params:  
        # Read in game data
        west_r=pd.read_csv(param["BASE_PATH"] + param["DATA_PATH"],encoding= 'unicode_escape').dropna(subset = ['mT1P1', 'mT1P2', 'mT2P1',"mT2P2"]).reset_index(drop=True)

        # Create tournemtnand dvisions combinations to play and teh order they occur in
        west_r_c=west_r[['tourney','Division',"Date"]].drop_duplicates().reset_index(drop=True)
        west_r_c["order"]=[list(dict.fromkeys(west_r_c["tourney"])).index(x)for x in west_r_c["tourney"]]

        # Add date data
        date_format = '%y-%m-%d'
        west_r_c["Date"]=[datetime.strptime(x, date_format)for x in west_r_c["Date"]]
    
        
        # Run elo model for whole timeframe
        test = GLICKO_ADD(
            sep=1500,
            remove=param["remove"],
            team_method=param["team_method"],
            avg_mu=param["avg_mu"],

            # RD bounds
            rd_min=param["RD_MIN"],      # ~80.36


            # team uncertainty (inv-var)
            team_var_alpha=param["team_var_alpha"],   # ~1.317
            inv_var_gamma=param["inv_var_gamma"],

            # RD shrink cap
            cap_redux=param["cap_redux"],
            max_reduction_frac=param["max_reduction_frac"],  # ~0.6699

            # volatility learning
            tau=param["tau"],  # ~0.491

            # inactivity RD inflation curve (your chosen saturating form)
            rd_inflation_mode=param["rd_inflation_mode"],
            time_constant=param["time_constant"],         # time_constant_phi
            buffer_days=param["buffer_days"],
            decay_tau_days=param["decay_tau_days"],   # 547.5
            sat_power=param["sat_power"],

            # kept for compatibility (ignored in saturating mode)
            convexity=param["convexity"],
            de=param["DE"],
            dc=param["DC"],
        )
        test.record_season_fast(west_r,west_r_c)
        print("Brier Score: ", test.brier_score(mg=20))

        # Export player results at all stages
        out_df = test.give_players_all()
        out_df.to_csv(param["BASE_PATH"] + "data/test_final_players_"+param["EXPORT_FILENAME"]+"_"+datetime.today().strftime('%Y-%m-%d')+".csv")
        # Export games
        all_games = test.played_games
        all_games.to_csv(param["BASE_PATH"] + "data/test_all_games_"+param["EXPORT_FILENAME"]+"_"+ datetime.today().strftime('%Y-%m-%d')+".csv")


if __name__=="__main__":
    main()