from src.tasks.refresh_elo_rankings import preprocess_tourney_data

DAG_NAME = "refresh_elo_rankings"


def main():
    print(f"Starting DAG: {DAG_NAME}")

    # Task to preprocess the tournament data
    preprocess_tourney_data.run()

    # Refreshing the rankings

    # Updating the frontend

    print(f"Completed DAG: {DAG_NAME}")


if __name__ == "__main__":
    main()
