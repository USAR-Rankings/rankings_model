import math
import random as random
import plotly.express as px


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
    cur_distance = max(player_elo - elo_ot, 0) + 50
    part_dist = max(elo_partner - elo_ot, 0) + 50
    cur_player_distance_proportion = cur_distance / (cur_distance + part_dist)

    if winner == True:
        expected = 1 - (cutoff)
        total_points = 2 * (player_elo * expected)
        points = total_points * (elo_partner / (elo_partner + player_elo))
    else:
        expected = 0 - cutoff
        total_points = 2 * (k * expected)
        points = total_points * cur_player_distance_proportion

    return points


def create_player_comparison_chart(out_df, track_players, param):
    track_df = out_df[out_df["name"].isin(track_players)]
    fig = px.line(track_df, x="Date", y="elo", color="name")
    fig.write_image(param["BASE_PATH"] + "data/track_players_elo.png")