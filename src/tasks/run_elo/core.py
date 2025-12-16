import pandas as pd
import numpy as np
import scipy as sp
import math
import copy
import random as random
import itertools
from itertools import chain
import warnings
warnings.filterwarnings(action='once')
import random
from datetime import date,datetime
from src.tasks.run_elo.helpers import * 


class Player:
    """
    A class to track the stats of an individual player.

    ...

    Attributes
    ----------
    name : str
        Name of the player.
    division : str
        The name of the first division the player played in.
    tournies : list of str
        List containing all the tournaments a player has played in.
    games : int
        The number of individual games a player has played.
    elo : float
        The rating of the player.

    Methods
    -------
    add_tounrey(self, tourney):
        Appends an additional tournament to the player's list of tournaments.
    update_elo(self, elo_ot, k1, k2, n, winner):
        Updates a player's Elo rating based on a given game.
    add_division(self, div):
        Updates the player's highest division.
    decay_rating(self, percent):
        Decays the player's rating based on a percentage.
    update_last_played(self, date):
        Updates the date when the player last played.
    update_time(self, date):
        Updates the days since the player last played and decays their rating accordingly.
    """
        
    def __init__(self, name,time_since_play=0,games=0, elo=1500,k_array=[],div_k=False,start_k=True):
        """
        Constructs all the necessary attributes for the player object.

        Parameters
        ----------
        name : str
            Name of the player.
        division : str
            The name of the first division the player played in.
        tournies : list of str, optional
            List containing all the tournaments a player has played in (default is an empty list).
        time_since_play : int, optional
            The number of days since the player last played (default is 0).
        games : int, optional
            The number of individual games a player has played (default is 0).
        elo : float, optional
            The rating of the player (default is 1500).
        """
        self.name = name
        self.elo = elo
        self.highest_division=10
        self.games=games
        self.tournies=[]
        self.days_since_played=time_since_play
        self._og_elo=self.elo
        self.k_array=k_array
        self.div_k=div_k
        self.start_k=start_k
        if self.start_k ==True:
            self.ng= self.k_array[-1]


        
        
    def add_tounrey(self,tourney):
        """
        Adds a tournament to the player's list of tournaments played.

        Parameters
        ----------
        tourney : str
            Name of the tournament played.
        """
        # Add Tournamnet
        self.tournies=self.tournies+[(tourney)]
        
        
        
        # Reset og elo
        self._og_elo=self.elo
    
        
    
    def update_elo(self,elo_ot,winner,pre_calc=False,odds=.5):
        """
        Updates a player's Elo rating from a given game.

        Parameters
        ----------
        elo_ot : float
            The average Elo of the other team.
        k1 : int
            The original factor by which the Elo is updated.
        k2 : int
            The factor by which the Elo is updated after n games.
        n : int
            The number of games after which the k factor changes.
        winner : bool
            Did the player win this game.

        Returns
        -------
        float
            The change in Elo rating for the player.
        """

        #Caculate win if need be
        if pre_calc==True:
            cutoff=odds
        else:
            cutoff=calculate_win_prob(elo_ot,self.elo)

        if winner ==True:
            expected=1-(cutoff)
        else:
            expected=0-cutoff
            
        
        self.elo+= self.k * expected
        self.games+=1
        if self.start_k==True:
            if self.games==self.ng+1:
                self.set_k()
        self._og_elo=self.elo
        
        return self.k * expected
    
    def add_division(self,div):
        """
        Updates the player's highest division.

        Parameters
        ----------
        div : int
            The division the player played in.
        """
        #set previous value
        prev=self.highest_division
        # Update highest division
        self.highest_division=min(self.highest_division,div)
        
        # If division has chnaged Update K value
        if (self.div_k==True) & (prev >self.highest_division):
            self.set_k()

        
    def decay_rating(self,percent):
        """
        Decays the player's rating based on a percentage.

        Parameters
        ----------
        percent : float
            The percentage by which the rating decays.
        """
        # if player hasn't played decay thier rating
        self.elo= self._og_elo*(1-(percent/100))
        
    def update_last_played(self,date):
        """
        Updates the date when the player last played.

        Parameters
        ----------
        date : datetime
            The date when the player last played.
        """
        self.last_played=date
        
    def update_time(self,date, decay_array):
        """
        Updates the days since the player last played and decays their rating accordingly.

        Parameters
        ----------
        date : datetime
            The current date.
        """
        self.days_since_played=abs(self.last_played-date).days

        if self.days_since_played > 365*2:
            self.decay_rating(decay_array[3])
        elif self.days_since_played > 365:
            self.decay_rating(decay_array[2])
        elif self.days_since_played > 30*6:
            self.decay_rating(decay_array[1])
        elif self.days_since_played > 91:
            self.decay_rating(decay_array[0])

    def set_k(self):
        if (self.start_k == True):
            if self.games <= self.ng:
                self.k=self.k_array[-2]
            else:
            #If not div specific k then k2 which should be in first spot
                self.k=self.k_array[0]
        else:
            # If over limit, set k to div specific k
            self.k=self.k_array[self.highest_division]
        
    
    
class ELO_Model:
    """
    A class that has is able to fun a elo calucuations and store results.

    ...

    Attributes
    ----------
    pdict : dictionary
        dictionary of player objects that stores players stats
    k1 : int
        The k value for the introductory period of players
    k2 : int
        The k value for the remainder of players games
    ng : int
        The number of individual games a player has to player before changing k values
    dc : int
        The amounto of elo Contender players start below the premier divsions
    de : int
        The amounto of elo Expert players start below the premier divsions
    tab : dataframe
        Tracks team stats across season
    played_games : dataframe
        Tracks games played so far and models predicted results
    temp_games: dataframe
        Holds games to be played by the model

    Methods
    -------
    
    """
        
    def __init__(self,k_array,dc,de,sep=2000,p_dict=[],tab=[],decay=False,decay_array=[],avg_team=False,start_per=50,start_k=True, div_k=False,remove=False, remove_time=365*1.5):
        """
        Constructs all the necessary attributes for the Elo model.

        Parameters
        ----------
        k1 : int
            The k value for the introductory period of players.
        k2 : int
            The k value for the remainder of players' games.
        ng : int
            The number of individual games a player has to play before changing k values.
        dc : int
            The amount of Elo Contender players start below the premier divisions.
        de : int
            The amount of Elo Expert players start below the premier divisions.
        sep : int, optional
            The starting Elo for players in the premier divisions (default is 2000).
        p_dict : dict, optional
            Dictionary of player objects that stores players' stats (default is an empty list).
        tab : DataFrame, optional
            Tracks team stats across the season (default is an empty list).
        """
        self.k_array=k_array
        self.dc=dc
        self.de=de
        self.sep=sep
        self.p_dict=p_dict
        self.tab=tab
        self.played_games=pd.DataFrame()
        self.predicted_games=pd.DataFrame()
        self.players_total=pd.DataFrame()
        self._div_dict={0:"Pro",1:"Premier",2:"Expert",3:"Contender"}
        self.decay=decay
        self.decay_array=decay_array
        self.avg_team=avg_team
        self.start_per=start_per
        self.start_k=start_k
        self.div_k=div_k
        self.remove=remove
        self.remove_time=remove_time
        
         
    
    
    def create_teams(self,data,tourney,division,date,avg_elo=False):
        """
        Constructs a new player dictionary and team table based on the first tournament.

        Parameters
        ----------
        data : DataFrame
            The DataFrame that contains the games to play on.
        tourney : str
            The tournament that you're starting with.
        division : str
            The division you're starting with.
        date : datetime
            The date of the tournament.
        avg_elo : bool, optional
            Whether to calculate average Elo for starting Elo (default is False).
        """
        # Sets starting elo based on the division
        if ("PREMIER" in division) or ( "PRO" in division):
            starting_elo=self.sep
            if("PRO" in division):
                div=0
            else: 
                div=1
        elif (("EXPERT" in division) or ("ELITE" in division) or ("ADVANCED" in division)or ("GOLD" in division) or ("WOMEN" in division)):
            starting_elo=self.sep-self.de
            starting_elo=self.sep-self.de
            div=2
        else:
            starting_elo=self.sep-self.dc
            div=3
        
        
        
        
        #Filter for tournament and divison
        filt_tab=data[(data["tourney"]==tourney)&(data["Division"]==division)]
        
        
        #Gets list of all players
        player_array=list(set(list(filt_tab["mT1P1"])+list(filt_tab["mT1P2"])+list(filt_tab["mT2P1"])+list(filt_tab["mT2P2"])))
        
        average_elo=[]
        if avg_elo == True:
            # Calculate average ELO
            for player in player_array:
                if player in self.p_dict.keys():
                    average_elo.append(self.p_dict[player].elo)
            
            start_elo=np.percentile(average_elo, self.start_per)
            
            # Set new starting elo
            starting_elo=start_elo
        
        if self.p_dict == []:
            #Create new player object for each player in the tournament and assign them the starting elo
            object_array=[Player(player,division,elo=starting_elo,div_k=self.div_k,start_k=self.start_k,k_array=self.k_array) for player in player_array]

             #Create the player dictionary where the player objects are stored
            self.p_dict= dict(zip(player_array, object_array))
            for player in player_array:
                self.p_dict[player].add_tounrey(tourney)
                self.p_dict[player].add_division(div)
                self.p_dict[player].set_k()
                self.p_dict[player].update_last_played(date)
                
            
            
        else:
            # Checks if player already exists, if not creates a new object for them
            for player in player_array:
                if player in self.p_dict:
                    if self.decay==True:
                        self.p_dict[player].update_time(date,self.decay_array)
                    self.p_dict[player].add_tounrey(tourney)
                    self.p_dict[player].add_division(div)
                    self.p_dict[player].update_last_played(date)
                    
                    
                else:
                    self.p_dict[player]=Player(player,division,elo=starting_elo,div_k=self.div_k,start_k=self.start_k,k_array=self.k_array)
                    self.p_dict[player].add_tounrey(tourney)
                    self.p_dict[player].add_division(div)
                    self.p_dict[player].set_k()
                    self.p_dict[player].update_last_played(date)

        
        
    def read_games(self,data,tourney,division="PREMIER"):
        """
        Reads in a table of games to be played to temporary games.

        Parameters
        ----------
        data : DataFrame
            The DataFrame that contains the games to play on.
        tourney : str
            The tournament that you're starting with.
        division : str, optional
            The division you're starting with (default is "PREMIER").
        """
        #Filter for data and rename columns
        data=data[(data["tourney"]==tourney)&(data["Division"]==division)].dropna(subset=["mT1_result"]).reset_index(drop=True)
        # Filter out ties
        data=data[(data["mT1_result"]!=0.5)].reset_index(drop=True)
        # Save to object
        self.temp_games=data
        
        
    def record_game(self,player1,player2,player3,player4,winner,index):
        """
        Creates and stores prediction and updates players' Elo.

        Parameters
        ----------
        player1 : str
            Name of the first player in the game.
        player2 : str
            Name of the second player in the game.
        player3 : str
            Name of the third player in the game.
        player4 : str
            Name of the fourth player in the game.
        winner : int
            The winner of the game (1 or 2).
        index : int
            Index of the game in the DataFrame.
        """
        #Pulls the player object of those in the game
        player1=self.p_dict[player1]
        player2=self.p_dict[player2]
        player3=self.p_dict[player3]
        player4=self.p_dict[player4]
        players=[player1,player2,player3,player4]            

        #Calculates the average elo for the match and the minimum number of games of any of the players in the match
        #Used for quality control purposes
        avg=0
        min_games=[]
        for player in players:
            avg+=player.elo
            min_games.append(player.games)

        #Adds this information to the game dataframe
        self.temp_games.at[index,"Avg Elo"]=avg/4
        self.temp_games.at[index,"Min Games"]=min(min_games)

        #pulls the elo of the team from the standings dataframe
        elo1=(player1.elo+player2.elo)/2
        elo2=(player3.elo+player4.elo)/2

        #print([player1.elo,player2.elo,player3.elo,player4.elo])
        #prob team 2 wins
        cutoff=calculate_win_prob(elo1,elo2)

        # Add player elos
        self.temp_games.at[index,"T1P1 ELO"]=player1.elo
        self.temp_games.at[index,"T1P2 ELO"]=player2.elo
        self.temp_games.at[index,"T2P1 ELO"]=player3.elo
        self.temp_games.at[index,"T2P2 ELO"]=player4.elo
        
        #Case if team 1 wins
        if (winner == 1) :
            
            # Updating the Elo Ratings
            self.temp_games.at[index,"T1P1 Change"]=player1.update_elo(elo2,pre_calc=self.avg_team,odds=cutoff,winner=True)
            self.temp_games.at[index,"T1P2 Change"]=player2.update_elo(elo2,pre_calc=self.avg_team,odds=cutoff,winner=True)
            self.temp_games.at[index,"T2P1 Change"]=player3.update_elo(elo1,pre_calc=self.avg_team,odds=cutoff,winner=False)
            self.temp_games.at[index,"T2P2 Change"]=player4.update_elo(elo1,pre_calc=self.avg_team,odds=cutoff,winner=False)
            self.temp_games.at[index,"Win"]= False

        # Case if team 2 wins

        else :
        
            # Updating the Elo Ratings
            self.temp_games.at[index,"T1P1 Change"]=player1.update_elo(elo2,pre_calc=self.avg_team,odds=cutoff,winner=False)
            self.temp_games.at[index,"T1P2 Change"]=player2.update_elo(elo2,pre_calc=self.avg_team,odds=cutoff,winner=False)
            self.temp_games.at[index,"T2P1 Change"]=player3.update_elo(elo1,pre_calc=self.avg_team,odds=cutoff,winner=True)
            self.temp_games.at[index,"T2P2 Change"]=player4.update_elo(elo1,pre_calc=self.avg_team,odds=cutoff,winner=True)
            #Win defaluts to false
            self.temp_games.at[index,"Win"]= True

        #updates win lose in the standings file
        
        #saves win prob to games df
        self.temp_games.at[index,"prob"]=cutoff
    
    #Plays an entire tournament including new team creation
    def record_tourney(self,data,tourney,division,date,avg_elo=False):
        """
        Plays through an entire tournament.

        Parameters
        ----------
        data : DataFrame
            The DataFrame that contains the games to play on.
        tourney : str
            The tournament that you're playing.
        division : str
            The division you're playing.
        date : datetime
            The date of the tournament.
        avg_elo : bool, optional
            Whether to calculate average Elo for starting Elo (default is False).
        """
        self.create_teams(data,tourney,division,date,avg_elo)
        self.read_games(data,tourney,division)
        zero_columns_to_add = ["T1P1 Change", "T1P2 Change", "T2P1 Change", "T2P2 Change","T1P1 Change","T1P1 ELO","T1P2 ELO","T2P1 ELO","T2P2 ELO","Min Games","Avg Elo",]
        self.temp_games["prob"]=[0.00]*len(self.temp_games)
        self.temp_games["Win"]=[True]*len(self.temp_games)
        
        for col in zero_columns_to_add:
            self.temp_games[col] = [0.00]*len(self.temp_games)
        for index,row in self.temp_games.iterrows():
                self.record_game(row["mT1P1"],row["mT1P2"],row["mT2P1"],row["mT2P2"],row["mT1_result"],index)
        self.played_games=self.played_games._append(self.temp_games,ignore_index=True)

    
    def record_season(self,data,combos):
        """
        Plays through multiple tournaments.

        Parameters
        ----------
        data : DataFrame
            The DataFrame that contains the games to play on.
        combos : DataFrame
            The combinations of tournament and division to play on.
        """
        # Loop through each tournamnt
        for j in combos["order"].unique():
            combos_t= combos[combos["order"]==j].reset_index(drop=True)
            #print(combos_t["tourney"][0])
            for i in range(0,len(combos_t)):
                print(combos_t.loc[i,"tourney"],combos_t.loc[i,"Division"])
                if "AVG_ELO" in combos_t.columns:
                    self.record_tourney(data,combos_t.loc[i,"tourney"],combos_t.loc[i,"Division"],combos_t.loc[i,"Date"],avg_elo=combos_t.loc[i,"AVG_ELO"])
                else:
                    self.record_tourney(data,combos_t.loc[i,"tourney"],combos_t.loc[i,"Division"],combos_t.loc[i,"Date"])
            
            #Update days since played and decay ratings
            if self.decay==True:
                for player in self.p_dict.values():
                    player.update_time(combos_t.loc[i,"Date"],self.decay_array)
            
            if self.remove == True:
                players = list(self.p_dict.keys())  # Create a list of keys to avoid modifying during iteration
                for player in players:
                    if self.p_dict[player].days_since_played > self.remove_time:
                        del self.p_dict[player]  # Safe to delete now
            # Update tourney level results
            self.players_total=self.players_total._append(self.give_players_df(combos_t.loc[i,"tourney"],combos_t.loc[i,"Date"]))
            
            
            
            
    def brier_score(self,mg):
        """
        Gives the brier score for matches with at least a certian number of games
        
        Parameters
        ----------
            mg : int
                The minimum number of games a player needs to count for the rankings
    
    
        """
        games=self.played_games.loc[self.played_games["Min Games"]>=mg]
        return(sum(((games["prob"]-games["Win"]*1))**2)/len(games))
        
    def give_players_old(self):
        """
        Returns DataFrame of players' stats.

        Returns
        -------
        DataFrame
            DataFrame containing players' names, Elo, games played, tournaments played, days since last played, and highest division.
        """
        players=list(self.p_dict.values())
        players.sort(key=lambda x: x.elo)
        avg_elo=0
        for player in players:
            print(""+str(player.name) + ": " +str(player.elo) +" Games: "+ (str(player.games)))
            avg_elo+=player.elo
            
    def give_players_df(self,tourney=[],date=[]):
        data = []

        for player_name, player_obj in self.p_dict.items():
            data.append([player_obj.name, player_obj.elo, player_obj.games, len(player_obj.tournies), player_obj.days_since_played,self._div_dict[player_obj.highest_division]])

        
        df = pd.DataFrame(data, columns=['name', 'elo', 'game', 'tournies', 'days_since_played',"Highest_Division"])
        # Sorting by elo
        df = df.sort_values(by='elo', ascending=False).reset_index(drop=True)
        if tourney != []:
            df["Date"]=[date]*len(df)
            df["Tournament"]=[tourney]*len(df)
        df=df.rename(columns={'game':'Games_Played' , 'tournies':'Tournaments_Played' })
        
        return df
    
    def give_players_all(self):
        """
        Returns DataFrame of all players' stats.

        Returns
        -------
        DataFrame
            DataFrame containing players' names, Elo, games played, tournaments played, days since last played, and highest division.
        """
        return self.players_total.reset_index(drop=True)
    
    def predict_game(self,player1,player2,player3,player4,winner,index):
        """
        Creates and stores predictions for a game.

        Parameters
        ----------
        player1 : str
            Name of the first player in the game.
        player2 : str
            Name of the second player in the game.
        player3 : str
            Name of the third player in the game.
        player4 : str
            Name of the fourth player in the game.
        winner : int
            The winner of the game (1 or 2).
        index : int
            Index of the game in the DataFrame.
        """
       #Pulls the player object of those in the game
        player1=self.p_dict[player1]
        player2=self.p_dict[player2]
        player3=self.p_dict[player3]
        player4=self.p_dict[player4]
        players=[player1,player2,player3,player4]            

        #Calculates the average elo for the match and the minimum number of games of any of the players in the match
        #Used for quality control purposes
        avg=0
        min_games=[]
        for player in players:
            avg+=player.elo
            min_games.append(player.games)
        
        #Adds this information to the game dataframe
        self.temp_games.at[index,"Avg Elo"]=avg/4
        self.temp_games.at[index,"Min Games"]=min(min_games)
        self.temp_games.at[index,"Max Games"]=max(min_games)

        #pulls the elo of the team from the standings dataframe
        elo1=(player1.elo+player2.elo)/2
        elo2=(player3.elo+player4.elo)/2

        
        #prob team 2 wins
        cutoff=calculate_win_prob(elo1,elo2)
        if cutoff <0.5:
            pred_win=1
        elif cutoff >.5:
            pred_win=0
        else:
            pred_win=""
            self.temp_games.at[index,"Predict_win"]=.5
        #Case if team 1 wins
        if (winner == 1) :
        

            if (pred_win== 0)&(cutoff!=.5):
                self.temp_games.at[index,"Predict_win"]=1
            self.temp_games.at[index,"Win"]= False

        # Case if team 2 wins

        else :
            

            if (pred_win== 0)&(cutoff!=.5):
                self.temp_games.at[index,"Predict_win"]=1
            self.temp_games.at[index,"Win"]= True

       
        #saves win prob to games df
        self.temp_games.at[index,"prob"]=cutoff
                
    def predict_tourney(self,data,tourney,division):
        """
        Predicts outcomes for an entire tournament.

        Parameters
        ----------
        data : DataFrame
            The DataFrame that contains the games to predict.
        tourney : str
            The tournament that you're predicting.
        division : str
            The division you're predicting.
        """
        self.create_teams(data,tourney,division)
        self.read_games(data,tourney,division)
        self.temp_games["prob"]=[0.00]*len(self.temp_games)
        self.temp_games["Win"]=[True]*len(self.temp_games)
        self.temp_games["Min Games"]=[0]*len(self.temp_games)
        self.temp_games["Avg Elo"]=[0]*len(self.temp_games)
        self.temp_games["Predict_win"]=[0.0]*len(self.temp_games)
        for index,row in self.temp_games.iterrows():
                self.predict_game(row["mT1P1"],row["mT1P2"],row["mT2P1"],row["mT2P2"],row["mT1_result"],index)
        self.predicted_games=self.predicted_games._append(self.temp_games,ignore_index=True)
        
    def predict_season(self,data,combos):
        """
        Predicts across multiple tournaments.

        Parameters
        ----------
        data : DataFrame
            The DataFrame that contains the games to predict.
        combos : DataFrame
            The combinations of tournament and division to predict.
        """
        for i in range(0,len(combos)):
            self.predict_tourney(data,combos.loc[i,"tourney"],combos.loc[i,"Division"])
        self.predicted_games=self.predicted_games.dropna(subset = ['Predict_win']).reset_index()