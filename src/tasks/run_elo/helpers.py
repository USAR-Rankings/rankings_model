import math
import random as random


def calculate_win_prob(elo1,elo2):
    """
        Calculates the probability of the second elo winning based on mathematical formula

        Parameters
        ----------
            elo1 : float
                an elo rating 
            elo2 : float
                an elo rating
        """
    return 1.0 * 1.0 / (1 + 1.0 * math.pow(10, 1.0 * (elo1 - elo2) / 400))

def team_elo_obj(player1,player2):
        """
        Calculates the teams elo based on the two players elos

        Parameters
        ----------
            player1 : Player object
                The player  object for the first team member
            player2 : Player object
                The player  object for the second team member
        """
        return(player1.elo+player2.elo)/2