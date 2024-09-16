import pandas as pd
import random as random
import itertools as itertools


# Creating a Pool class that plays out a pool This current iteration is set up to play two games only (STS/USAR Format but could be modifed)
class Pool():
    """
    Represents a pool in a tournament.

    Attributes:
    - teams (list): List of team names in the pool.
    - team_dict (dict): Dictionary mapping team names to their ratings.
    - stand (pandas.DataFrame): DataFrame to store pool standings.
    """
    
    def __init__(self,teams,team_dict,hot=False,k=50):
        """
        Initializes a Pool object.

        Parameters:
        - teams (list): List of team names in the pool.
        - team_dict (dict): Dictionary mapping team names to their ratings.
        """
        self.teams=teams
        self.team_dict=team_dict
        self.stand=pd.DataFrame({"Team":teams,"RD":[0.00]*len(teams),"GW":[0]*len(teams),"GL":[0]*len(teams),"Rating":[team_dict[team] for team in teams ]})
        self.hot=hot
        self.k=k

    def _pool_match(self,team_1,team_2,i1,i2):
        """
        Simulates a match between two teams in the pool and updates standings.

        Parameters:
        - team_1 (str): Name of the first team.
        - team_2 (str): Name of the second team.
        - i1 (int): Index of the first team in the standings DataFrame.
        - i2 (int): Index of the second team in the standings DataFrame.
        """
        games=0
        self.stand.at[i1,"RD"]+=self.team_dict[team_1]-self.team_dict[team_2]
        self.stand.at[i2,"RD"]+=self.team_dict[team_2]-self.team_dict[team_1]
        
        #Here is where you could modify to only play one game or use the best of 3 function to play a seris
        while (games<2):
            winner =self.play_game(team_1,team_2)
            if winner==team_1:
                wi=i1
                li=i2
            else:
                wi=i2
                li=i1
            self.stand.at[wi,"GW"]+=1
            self.stand.at[li,"GL"]+=1
            games += 1
    
    def sim(self):
        """Simulates all matches within the pool."""
        #crate a list of all possible matchs
        combinations = list(itertools.combinations(range(0,len(self.stand)), 2))
        
        for combo in combinations:
            # Play all possible matches
            self._pool_match(self.teams[combo[0]],self.teams[combo[1]],combo[0],combo[1])
            
        # self.pool_match(self.teams[0],self.teams[3],0,3,td)
        # self.pool_match(self.teams[1],self.teams[2],1,2,td)
        # self.pool_match(self.teams[0],self.teams[1],0,1,td)
        # self.pool_match(self.teams[2],self.teams[3],2,3,td)
        # self.pool_match(self.teams[0],self.teams[2],0,2,td)
        # self.pool_match(self.teams[1],self.teams[3],1,3,td)
    #insert tiebrakers
        
        #["Team","MW","ML","GW","GL","Rating"]
        self.stand["RD"]=self.stand["RD"]/len(self.stand)
        #print(self.team_dict)
        #self.stand["Rating"]=[team_dict[team] for team in self.stand["Team"] ]
        
    def give_seeds(self,tag):
        """
        Generates seedings for the pool. This is used only for slotted bracket tournaments

        Parameters:
        - tag (str): A tag to identify the seedings.

        Returns:
        - dict: A dictionary mapping seed identifiers to team names.
        """
        return (dict(zip([tag+"1",tag+"2",tag+"3",tag+"4"], self.stand["Team"])))


    # This is the function that plays a game between two teams and returns a randomly generated winner based on the teams rating
    def play_game(self,team1,team2):
        cutoff=calc_prob(self.team_dict[team1],self.team_dict[team2])
        #Generates a random number between 0 and 1
        result=random.uniform(0, 1)
       
        #If value is above cutoff team 1 wins
        if result>cutoff:
            winner=team1
            loser=team2
            if self.hot==True:
                self.team_dict[team1]+=self.k * (1-(1-cutoff))
                self.team_dict[team2]+=self.k * (0-cutoff)
        #If not team 2 wins
        else:
            winner=team2
            loser=team1
            if self.hot==True:
                self.team_dict[team1]+=self.k * (0-(1-cutoff))
                self.team_dict[team2]+=self.k * (1-cutoff)
        
    
        return winner
    
    
    # This does the same thing but with a three game series 
    def best_of_3(self,team_1,team_2,td=team_dict):
        w_d={
                team_1:0,
                team_2:0
            }
        while ((w_d[team_1]<2)&(w_d[team_2]<2)):
            winner=self.play_game(team_1,team_2,team_dict=td)
            w_d[winner]+=1
        if w_d[team_1]==2:
            winner=team_1
        else:
            winner=team_2
        return winner
        
class Simulator():
    """
    Simulates a tournament.

    Attributes:
    - pools (list): List of pools in the tournament.
    - team_dict (dict): Dictionary mapping team names to their ratings.
    """
    def __init__(self,pools,team_dict,hot=False,k=50):
        """
        Initializes a Simulator object.

        Parameters:
        - pools (list): List of pools in the tournament.
        - team_dict (dict): Dictionary mapping team names to their ratings.
        """
        self.pools=pools
        self.team_dict=team_dict
        self.hot=hot
        self.k=k
        if self.hot == True:
            self.team_dict_o=copy.deepcopy(team_dict)
            self.team_dict_new=[]
        

# Helper function to simulate a pool
    def _sim_pool(self,pool):
        """
        Simulates matches within a pool and returns standings.

        Parameters:
        - pool (list): List of teams in the pool.

        Returns:
        - pandas.DataFrame: Standings DataFrame for the pool.
        """
        pool_obj=Pool(pool,self.team_dict,self.hot,self.k)
        pool_obj.sim()
        return(pool_obj.stand)
    
    # This was set up to determine things for a seeded bracket
    def _find_highest(self,rowA,rowB,rowC,team_dict_w):
        """
        Finds the team with the highest performance among three teams. THIS IS USED ONLY FOR SLOTTED BRACKETS WITH 3 pools

        Parameters:
        - rowA (pandas.Series): Standing of team A.
        - rowB (pandas.Series): Standing of team B.
        - rowC (pandas.Series): Standing of team C.
        - team_dict_w (dict): Dictionary mapping team names to their ratings.

        Returns:
        - str: Identifier of the team with the highest performance.
        """
        if (rowA["ML"]> rowB["ML"]) & (rowA["ML"]> rowC["ML"]):
            return "A"
        elif (rowB["ML"]> rowA["ML"]) & (rowB["ML"]> rowC["ML"]):
            return "B"
        elif (rowC["ML"]> rowA["ML"]) & (rowC["ML"]> rowB["ML"]):
            return "C"
        elif (rowA["GL"]> rowB["GL"]) & (rowA["GL"]> rowC["GL"]):
            return "A"
        elif (rowB["GL"]> rowA["GL"]) & (rowB["GL"]> rowC["GL"]):
            return "B"
        elif (rowC["GL"]> rowA["GL"]) & (rowC["GL"]> rowB["GL"]):
            return "C"
        elif (rowA["GW"]> rowB["GW"]) & (rowA["GW"]> rowC["GW"]):
            return "A"
        elif (rowB["GW"]> rowA["GW"]) & (rowB["GW"]> rowC["GW"]):
            return "B"
        elif (rowC["GW"]> rowA["GW"]) & (rowC["GW"]> rowB["GW"]):
            return "C"
        elif (team_dict_w[rowA["Team"]]> team_dict_w[rowB["Team"]]) & (team_dict_w[rowA["Team"]]> team_dict_w[rowC["Team"]]):
            return "A"
        elif (team_dict_w[rowB["Team"]]> team_dict_w[rowA["Team"]]) & (team_dict_w[rowB["Team"]]> team_dict_w[rowC["Team"]]):
            return "B"
        elif (team_dict_w[rowC["Team"]]> team_dict_w[rowA["Team"]]) & (team_dict_w[rowC["Team"]]> team_dict_w[rowB["Team"]]):
            return "C"
        else:
            return "A"

    
    # This logic for bracket generation 
    def _find_power_of_2(self,num):
        """
        Finds the power of 2 closest to a given number.

        Parameters:
        - num (int): Input number.

        Returns:
        - int: Power of 2 closest to the input number.
        """
        if num < 1:
            return None

        power = 0
        while num > 1:
            num //= 2
            power += 1

        return power

    def _generate_important_games(self,num_teams):
        """
        Generates a list of important games for the bracket.

        Parameters:
        - num_teams (int): Total number of teams in the tournament.
        """
    # This logic for bracket generation
        num_rounds=self._find_power_of_2(num_teams)
        running=0
        self._important_games=[]
        for i in range(num_rounds-1,0,-1):
            self._important_games.append(running+(2**i))
            running+=(2**i)
        

    # This simulates an individual bracket
    def _sim_bracket(self,seeds,keys):
        """
        Simulates a bracket based on seedings.

        Parameters:
        - seeds (list): List of seedings for the bracket.
        - keys (list): Keys for bracket generation.
        """
        seeds_dict = dict(zip([str(x) for x in range(1,len(seeds)+1)], seeds))
        teamlist=[seeds_dict.get(key) for key in keys]
        totalgames=(len(teamlist))-1
        roundid=0
        gameid=0
        nextround = []
        round_list = [teamlist]  # List to store rounds of the tournament

        self._generate_important_games(len(teamlist))

        while (gameid < totalgames):
            if gameid in self._important_games:
                #if a new round begins, reset the list of the next round
                #print ("--- starting a new round of games ---")
                round_list.append(nextround)
                teamlist = nextround
                nextround = []
                roundid = 0

            #compare the 1st entry in the list to the 2nd entry in the list
            homeid = teamlist[roundid]
            awayid = teamlist[roundid + 1]

            #the winner of the match become the next entry in the nextround list
            #more realistic metrics could be substituted here, but ID can be used for this example
            if homeid == "BYE":
                # If one team has a "BYE", the other team automatically wins
                winner = awayid
            elif awayid == "BYE":
                # If one team has a "BYE", the other team automatically wins
                winner = homeid
            else:
                winner=self.best_of_3(homeid,awayid)
            nextround.append(winner)
            if gameid==self._important_games[len(self._important_games) - 1]:
                round_list.append([winner])
            #increase the gameid and roundid
            gameid += 1
            roundid += 2
            self.round_list=round_list

    # This is the function that plays a game between two teams and returns a randomly generated winner based on the teams rating
    def play_game(self,team1,team2):
        cutoff=calc_prob(self.team_dict[team1],self.team_dict[team2])
        #Generates a random number between 0 and 1
        result=random.uniform(0, 1)
       
        #If value is above cutoff team 1 wins
        if result>cutoff:
            winner=team1
            loser=team2
            if self.hot==True:
                self.team_dict[team1]+=self.k * (1-(1-cutoff))
                self.team_dict[team2]+=self.k * (0-cutoff)
        #If not team 2 wins
        else:
            winner=team2
            loser=team1
            if self.hot==True:
                self.team_dict[team1]+=self.k * (0-(1-cutoff))
                self.team_dict[team2]+=self.k * (1-cutoff)
        
    
        return winner
    
    
    # This does the same thing but with a three game series 
    def best_of_3(self,team_1,team_2):
        w_d={
                team_1:0,
                team_2:0
            }
        while ((w_d[team_1]<2)&(w_d[team_2]<2)):
            winner=self.play_game(team_1,team_2)
            w_d[winner]+=1
        if w_d[team_1]==2:
            winner=team_1
        else:
            winner=team_2
        return winner

    
    
    # Runs one simulation all the way through
    def one_sim(self,num_teams,key_dict):
        """
        Runs one simulation of the tournament.

        Parameters:
        - num_teams (int): Total number of teams in the tournament.
        - key_dict (dict): Dictionary mapping number of teams to bracket keys.

        Returns:
        - tuple: A tuple containing standings for each pool, final standings, and bracket results.
        """
        # Set up standings
        div_stand=pd.DataFrame()

        # Simlulate all the pools
        self.pool_stand= [self._sim_pool(pool) for pool in self.pools]

        # Combine the pools to one standings
        div_stand=pd.concat(self.pool_stand)

        # Sort Standings by losses and then average rating diffential
        self.div_final=div_stand.sort_values(["GL","RD"],ascending=[True,False]).reset_index(drop=True)

        # Assign Seeds
        self.div_final["Seed"]=range(1,len(self.div_final)+1)

    
        # Assign byes
        num_byes = num_teams - len(self.div_final["Team"])
        byes=["BYE"] * num_byes
        seeds=list(self.div_final["Team"])+byes

        # Simulate bracket
        self._sim_bracket(seeds,key_dict[str(num_teams)])
        
        return(self.pool_stand,self.div_final,self.round_list)

    
class Multi_Simulator(Simulator):
    """
    Extends the Simulator class to perform multiple simulations.

    Methods:
    - sim_n(num_teams, n, key_dict): Simulates 'n' number of tournaments.
    - _get_sum_pool(pool, write=False, tag="", n=0): Returns summary of pool standings.
    - give_pools_summary(write=False, tag=""): Provides summary of all pools' standings.
    - give_seed_summary(write=False, tag=""): Provides summary of seedings.
    - give_bracket_summary(write=False, tag=""): Provides summary of bracket results.
    - export_results(tag): Exports simulation results to files.
    """
    # Simulate n number of tournaments
    def sim_n(self,num_teams,n,key_dict):
        """
        Simulates 'n' number of tournaments.

        Parameters:
        - num_teams (int): Total number of teams in the tournament.
        - n (int): Number of tournaments to simulate.
        - key_dict (dict): Dictionary mapping number of teams to bracket keys.

        Returns:
        - tuple: A tuple containing final standings, pool standings, and bracket results.
        """
        
        self.div_stands=[]
        self.div_finals=[]
        self.big_list=[]
        for i in range(1,n+1):
            if self.hot==True:
                self.team_dict=copy.deepcopy(self.team_dict_o)
            self.one_sim(num_teams=num_teams,key_dict=key_dict)
            # Add simulation numbers
            for div in self.pool_stand:
                div["sim"]=[i]*len(div)
            self.div_final["sim"]=[i]*len(self.div_final)

            # Keep track of all the results 
            self.div_stands.append(self.pool_stand)
            self.div_finals.append(self.div_final)
            self.big_list.append(self.round_list)

        # Sets up final results     
        self.div_final_con=pd.concat(self.div_finals)
        self.div_stands_con=[]
        for i in range(len(self.pools)):
            div_stands_l=[]
            for stand in self.div_stands:
                div_stands_l.append(stand[i])
            self.div_stands_con.append(pd.concat(div_stands_l))



        return(self.div_final_con,self.div_stands_con,self.big_list)
    
    def _get_sum_pool(self,pool,write=False, tag="",n=0):
        """
        Returns the summary of pool standings.

        Parameters:
        - pool (pandas.DataFrame): DataFrame containing pool standings.
        - write (bool): Whether to write summary to file.
        - tag (str): Tag for file name.
        - n (int): Simulation number.

        Returns:
        - pandas.DataFrame: Summary of pool standings.
        """
        # Returns the pool sorted by avg games won
        if write == True:
            pool[["Team","GW","GL","Rating"]].groupby("Team").mean().sort_values("GW",ascending=False).round(2).to_csv("{}_pool_{}.csv".format(tag,n+1))
        return(pool[["Team","GW","GL","Rating"]].groupby("Team").mean().sort_values("GW",ascending=False).round(2))
    
    def give_pools_summary(self,write=False, tag=""):
        """
        Provides a summary of all pools' standings.

        Parameters:
        - write (bool): Whether to write summary to file.
        - tag (str): Tag for file name.

        Returns:
        - list: List of pool standings summaries.
        """
        if write == True:
            [self._get_sum_pool(pool,write=write,tag=tag,n=i) for i,pool in enumerate(self.div_stands_con)]
        return[self._get_sum_pool(pool) for pool in self.div_stands_con]
    
    def give_seed_summary(self,write=False,tag=""):
        """
        Provides a summary of seedings.

        Parameters:
        - write (bool): Whether to write summary to file.
        - tag (str): Tag for file name.

        Returns:
        - pandas.DataFrame: Summary of seedings.
        """
        # Sorts by games won
        if write==True:
            self.div_final_con[["Team","GW","GL","Rating","Seed"]].groupby("Team").mean().sort_values("GW",ascending=False).round(2).to_csv("{}_seeds.csv".format(tag))
        return self.div_final_con[["Team","GW","GL","Rating","Seed"]].groupby("Team").mean().sort_values("GW",ascending=False).round(2)
    
    def give_bracket_summary(self, write=False,tag=""):
        """
        Provides a summary of bracket results.

        Parameters:
        - write (bool): Whether to write summary to file.
        - tag (str): Tag for file name.

        Returns:
        - pandas.DataFrame: Summary of bracket results.
        """
        big_list=self.big_list
        bracket=pd.DataFrame({"Round_32":[big_list[0][0]],"Round_16":[big_list[0][1]],"Round_8":[big_list[0][2]],"Semis":[big_list[0][3]],"Finals":[big_list[0][4]],"Champion":[big_list[0][5]]})
        for i in range(1,len(big_list)):
            bracket=pd.concat([bracket,pd.DataFrame({"Round_32":[big_list[i][0]],"Round_16":[big_list[i][1]],"Round_8":[big_list[i][2]],"Semis":[big_list[i][3]],"Finals":[big_list[i][4]],"Champion":[big_list[i][5]]})]).reset_index(drop=True)

        results=pd.DataFrame()
        for team in list(team_dict.keys()):
            rds=[]
            for step in list(bracket.columns)[1:len(list(bracket.columns))]:
                rds.append(sum([team in rd for rd in bracket[step]])/len(bracket))
            indi=pd.DataFrame({"Team":[team],"Round_16": [rds[0]*100],"Round_8": [rds[1]*100],"Semis":[rds[2]*100],"Finals":[rds[3]*100],"Champion":[rds[4]*100]})    
            results=pd.concat([results,indi])
        if write==True:
            results.sort_values(["Champion","Finals","Semis","Round_8","Round_16"],ascending=False).round(2).reset_index(drop=True).to_csv("{}_bracket.csv".format(tag))
        return results.sort_values(["Champion","Finals","Semis","Round_8","Round_16"],ascending=False).round(2).reset_index(drop=True)
    
    import pandas as pd

    def give_bracket_summary_scale(self, write=False, tag=""):
        """
        Provides a summary of bracket results.
    
        Parameters:
        - write (bool): Whether to write summary to file.
        - tag (str): Tag for file name.
    
        Returns:
        - pandas.DataFrame: Summary of bracket results.
        """
        big_list = self.big_list
        num_rounds = len(big_list[0])  # Assuming each item in big_list contains results for all rounds
    
        # Create DataFrame for bracket results
        bracket_columns = [f"Round_{2**i}" for i in range(num_rounds - 1, -1, -1)]
        bracket = pd.DataFrame(big_list, columns=bracket_columns)
    
        # Extract team names and remove "BYE" values
        team_names = [team for team in set(big_list[0][0]) if team != "BYE"]
        results_data = {"Team": team_names}
        # Calculate Team Based Statistics
        for i in range(num_rounds):
            round_name = f"Round_{2**i}"
            results_data[round_name] = [(sum(bracket[round_name].apply(lambda x: team in x)) / len(bracket))*100  for team in team_names]
        results = pd.DataFrame(results_data)
        # Sort columns in reverse order
        sort_columns = ["Team"] + [f"Round_{2**i}" for i in range(num_rounds - 2, -1, -1)]
        results = results[sort_columns]
    
        # Write to file if required
        if write:
            results.sort_values(sort_columns[1:], ascending=False).round(2).reset_index(drop=True).to_csv(f"{tag}_bracket.csv", index=False)
    
        return results.sort_values(sort_columns[1:], ascending=False).round(2).reset_index(drop=True)
        
    def export_results(self, tag):
        """
        Exports simulation results to files.

        Parameters:
        - tag (str): Tag for file names.
        """
        self.give_pools_summary(write=True, tag=tag)
        self.give_seed_summary(write=True, tag=tag)
        #self.give_bracket_summary(write=True, tag=tag)
        self.give_bracket_summary_scale(write=True, tag=tag)
        
    
