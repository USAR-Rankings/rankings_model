import pandas as pd
import random as random
from itertools import chain
import warnings
warnings.filterwarnings(action='once')
from datetime import date,datetime
from tasks.run_elo.core import *
#from ..tasks.run_elo.core import *
#from ..tasks.run_elo.helpers import *
from ..configs.run_elo_open import (DATA_PATH,
                                       NUMB_INITAL,
                                       K1,
                                       K2,
                                       NG,
                                       DC,
                                       DE,
                                       SEP,
                                       DECAY,
                                       DECAY_ARRAY,EXPORT_FILENAME)

def main():
    # Read in game data
    west_r=pd.read_csv(DATA_PATH,encoding= 'unicode_escape').dropna(subset = ['mT1P1', 'mT1P2', 'mT2P1',"mT2P2"]).reset_index(drop=True)
    
    
    # Create tournemtnand dvisions combinations to play and teh order they occur in
    west_r_c=west_r[['tourney','Division',"Date"]].drop_duplicates().reset_index(drop=True)
    west_r_c["order"]=[list(dict.fromkeys(west_r_c["tourney"])).index(x)for x in west_r_c["tourney"]]
    
    

    # Add date data
    date_format = '%y-%m-%d'
    west_r_c["Date"]=[datetime.strptime(x, date_format)for x in west_r_c["Date"]]
   
    # Touranments to avereg elo for starting elo
    west_r_c["AVG_ELO"]=[True if x >NUMB_INITAL  else False for x in west_r_c["order"]]
    
    # Run elo model for whole timeframe
    test=ELO_Model(K1,K2,NG,DC,DE,decay=DECAY, decay_array=DECAY_ARRAY)
    test.record_season(west_r,west_r_c)
    
    # Export player results at all stages
    test.give_players_all().to_csv("../../data/test_final_players_"+EXPORT_FILENAME+".csv")

    # Export games
    test.played_games.to_csv("../../data/test_final_games_"+EXPORT_FILENAME+".csv")