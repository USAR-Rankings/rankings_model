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
from src.tasks.run_elo.core import *
#from ..tasks.run_elo.core import *
#from ..tasks.run_elo.helpers import *
from src.configs.run_elo_open import (OPEN_P,WOMENS_P)

def main():
    params =[OPEN_P,WOMENS_P]  
    for param in params:  
        # Read in game data
        west_r=pd.read_csv(param["DATA_PATH"],encoding= 'unicode_escape').dropna(subset = ['mT1P1', 'mT1P2', 'mT2P1',"mT2P2"]).reset_index(drop=True)
        
        
        # Create tournemtnand dvisions combinations to play and teh order they occur in
        west_r_c=west_r[['tourney','Division',"Date"]].drop_duplicates().reset_index(drop=True)
        west_r_c["order"]=[list(dict.fromkeys(west_r_c["tourney"])).index(x)for x in west_r_c["tourney"]]
        
        

        # Add date data
        date_format = '%y-%m-%d'
        west_r_c["Date"]=[datetime.strptime(x, date_format)for x in west_r_c["Date"]]
    
        # Touranments to avereg elo for starting elo
        west_r_c["AVG_ELO"]=[True if x >param["NUMB_INITAL"]  else False for x in west_r_c["order"]]
        
        # Run elo model for whole timeframe
        test=ELO_Model(param["K1"],param["K2"],param["NG"],param["DC"],param["DE"],decay=param["DECAY"], decay_array=param["DECAY_ARRAY"])
        test.record_season(west_r,west_r_c)
        
        # Export player results at all stages
        test.give_players_all().to_csv("data/test_final_players_"+param["EXPORT_FILENAME"]+datetime.today().strftime('%Y-%m-%d')+".csv")

        # Export games
        test.played_games.to_csv("data/test_all_games_"+param["EXPORT_FILENAME"]+ datetime.today().strftime('%Y-%m-%d')+".csv")

main()