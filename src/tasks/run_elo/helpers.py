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

def test_elo_reaction(player_elo, elo_partner, elo_ot, winner, k):
    """
    Used to run a quick test on how the current ELO model implementation would react to a given situation
    :float player_elo: The current player's ELO score
    :float elo_partner: Their partner's ELO
    :float elo_ot: The other team's ELO
    :bool winner: True if this player won the match, false ow
    :float k: the K value used
    :return:  float, the amount the player's ELO would change in this scenario
    """
    cutoff = calculate_win_prob(elo_ot, (player_elo + elo_partner) / 2)
    cur_distance = max(player_elo - elo_ot, 0) + 500
    # cur_distance = cur_distance if cur_distance > 0 else 1
    # 100 to make it less sensitive when the ELO scores are the same as the other team
    part_dist = max(elo_partner - elo_ot, 0) + 500
    # part_dist = part_dist if part_dist > 0 else 1
    # This finds the proportion of distance the current player is accountable for
    cur_player_distance_proportion = cur_distance / (cur_distance + part_dist)

    if winner == True:
        expected = 1 - (cutoff)
        total_points = 2 * (k * expected)
        # points = total_points * (1 - cur_player_distance_proportion)
        if player_elo < elo_partner:
            points = total_points * 0.6
        else:
            points = total_points * 0.4
    else:
        expected = 0 - cutoff
        total_points = 2 * (k * expected)
        # points = total_points * cur_player_distance_proportion
        points = total_points / 2

    ratio = elo_partner / (player_elo + elo_partner)
    if player_elo < elo_partner:
        ratio = ratio if ratio >= 0.6 else 0.6
        # ratio = 0.5
        points = total_points * ratio
    else:
        ratio = ratio if ratio <= 0.4 else 0.4
        # ratio = 0.5
        points = total_points * ratio

    return points