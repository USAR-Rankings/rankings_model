from src.tasks.find_name_corrections import generate_corrections

DAG_NAME = "find_name_corrections"

def main():
    print(f"Starting DAG: {DAG_NAME}")
    # Task to generate the actual proposed name corrections
    generate_corrections.run()

    print(f"Completed DAG: {DAG_NAME}")


if __name__ == "__main__":
    main()
