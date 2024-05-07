import math
import random as random



# This sets up the seeding for the bracket portion of the tournament
# You can add the logic here for any custom seeding you might want
bracket_keys={
    "Open":["A1","C4","B2","D3","D1","A4","C2","B3","B1","D4","A2","C3","C1","B4","A3","D2"],
    "A":["A1","BYE","B3","C3","A2","BYE","C2","B4","B1","BYE","A3","C4","C1","BYE","B2","A4"],
    "B":["A1","BYE","B3","C3","B2","BYE","C2","A4","B1","BYE","A3","C4","C1","BYE","A2","B4"],
    "C":["A1","BYE","B3","C3","C2","BYE","B2","A4","B1","BYE","A3","C4","C1","BYE","A2","B4"],
    "8":['1', '8', '4', '5', '2', '7', '3', '6'],
    "16":['1', '16', '8', '9', '4', '13', '5', '12', '2', '15', '7', '10', '3', '14', '6', '11'],
    "32":['1', '32', '16', '17', '8', '25', '9', '24', '4', '29', '13', '20', '5', '28', '12', '21', '2', '31', '15', '18', '7', '26', '10', '23', '3', '30', '14', '19', '6', '27', '11', '22'],
    "64": ['1', '64', '32', '33', '16', '49', '17', '48', '8', '57', '25', '40', '9', '56', '24', '41', '4', '61', '29', '36', '13', '52', '20', '45', '5', '60', '28', '37', '12', '53', '21', '44', '2', '63', '31', '34', '15', '50', '18', '47', '7', '58', '26', '39', '10', '55', '23', '42', '3', '62', '30', '35', '14', '51', '19', '46', '6', '59', '27', '38', '11', '54', '22', '43']
}


# This is used to calculated the probablity of team two winning the match based on out rating system
# You should update to be the function on your elo system
def calc_prob(score1,score2):
    #Probablity team 2 wins
    return 1.0 * 1.0 / (1 + 1.0 * math.pow(10, 1.0 * (score1 - score2) / 400))

def create_pools(dict,num_pools):
    teams = list(dict.keys())
    final=[[] for _ in range(num_pools)]
    max_number_teams=math.ceil(len(teams)/num_pools)
    order=([x for x in range(num_pools)]+([x for x in range(num_pools)][::-1]))*math.ceil(max_number_teams/2)
    while len(teams)>0:
        final[order.pop(0)].append(teams.pop(0))
    return(final)
        
 
# This is the function that plays a game between two teams and returns a randomly generated winner based on the teams rating
def play_game(team1,team2,team_dict=team_dict):
    cutoff=calc_prob(team_dict[team1],team_dict[team2])
    #Generates a random number between 0 and 1
    result=random.uniform(0, 1)
   
    #If value is above cutoff team 1 wins
    if result>cutoff:
        winner=team1
        loser=team2
    #If not team 2 wins
    else:
        winner=team2
        loser=team1


    return winner


# This does the same thing but with a three game series 
def best_of_3(team_1,team_2,td=team_dict):
    w_d={
            team_1:0,
            team_2:0
        }
    while ((w_d[team_1]<2)&(w_d[team_2]<2)):
        winner=play_game(team_1,team_2,team_dict=td)
        w_d[winner]+=1
    if w_d[team_1]==2:
        winner=team_1
    else:
        winner=team_2
    return winner

