<p align="center">
  <img src="[http://some_place.com/image.png](https://github.com/USAR-Rankings/rankings_model/assets/60453676/d8f53b03-0950-44c4-8caf-719aeb002314)" />
</p>

# USAR Rankings Model

This repo serves to hold all code related to the USAR Rankings model. It holds all code
that the USAR Rankings committee uses to refresh the rankings after each tournament 
and experiments conducted to find the best model to use.

## Enviroment Setup
To start, please clone this directory to your local folder. After doing so, you will
need to do the following steps:
1. Install all python requirements into a virtual environment
2. Setup the .env file with relevant information
3. Download all input data needed from the USAR google drive to local  

### Installing python requirements
To install the python requirements, simply run the command:  
```pip install -r requirements.txt```  

### Setting up the env file
There is an .env_template file provided as an example. Please copy and paste
this file into the same directory, and rename it as ".env". This file will hold
all secret information that should not be publically released to github.
Please replace the placeholder variable values with whatever is relevant to the
enviroment that you are using (for ex, the path to your input data, output data,
where the repo is stored, etc). Later, we will also store any passwords related
to publishing the rankings to the USAR webpage here as well.

### Downloading all input data
Please login to the USAR google drive account and download the "Rankings_Data" 
folder. This has all the data you will need to run the pipeline. Going forward,
please keep the USAR google drive folder updated with all data. This will serve
as the centralized storage for all data needed by the USAR Rankings committee.

## Running the pipeline
Now that the environment setup is complete, you can either run the pipeline
from an IDE or the command line. To run from the command line, follow these
steps:
1. Navigate to the top level folder of the repo
2. Run the the command ```python -m src.dags.refresh_rankings_model```

To run from an IDE, follow these steps:
1. Open your preferred IDE
2. Add the rankings_model (top level of this repo) to the PYTHONPATH (or the source) using the IDE's settings
3. Run the refresh_rankings_model.py file (or any relevant DAG)

If you want to run this for actual deployment, please do so from the google
collab file. Please navigate to the USAR google drive, and there will be a google
collab file titled "cli_runner.ipynb". All you need to do is hit run all on this
file and you can run the pipeline remotely. Please utilize this for any actual
deployments, and utilize your local environment when developing.

## Best practices for development
The following is some notes pertaining to best practices to use while pushing
any code to this repo.

### General structure

To start, please ensure that no single script performs too many tasks. Please
split each script into its parts, and then add those parts to the relevant DAG.
For example, when refreshing the rankings, we can break this down into several 
tasks being:
1. Scrape new data
2. Preprocess data
3. Train model and generate rankings
4. Post process rankings
5. Publish rankings

We then have a single python file which runs each of these tasks. Within each
task, the actual actions are performed. If a single task has too many actions,
we will split that another level deeper. This allows us to continually add more
code to the repo but keep everything readable. It should be easy for anyone to 
navigate to what they are looking for starting at the DAG level and then 
clicking down levels until they find the code they want to edit.

### Individual scripts
Please break each script into a main run function and supporting helper functions
to ensure readability. At the bottom of every script, please have a run function
which acts as a main runner. Then, above that runner will be all other functions.
This helps us to quickly scroll to the run function to see what is happening,
and then drill down into a relevant helper function when we want to see that
level of detail.

All individual tasks / scripts should have limited information directly passed between
them. Unless absolutely necessary, each task should start by reading in the needed
data, then performing operations, then writing this data back out (note: please
use the provided read / write functions from the utils folder for this). This
is the easiest way to allow us to code freely in both Python and R.

An example outline of a single task / script is below:

- Brief string stating purpose of script
- import statements
- helper functions
- main run function
  - read data needed
  - perform operations (call helper functions)
  - write data out
- if script is ran directly
  - perform the run function

### Miscellaneous
#### Read / write functions
Please use the read / write functions from the utils folder for any reading / 
writing of data. This helps to ensure that we can easily update these functions
to support any environment we choose to use in the future.

#### Constants 
Please do not use the actual name of a file when reading it in. There will be times
when we have a dated file, and we want to easily change that file out. If we 
hardcode this file name across the pipeline, it will be difficult to do so. 
If you want to read a file in, please define the file name in the configs/constants
file. Then, import that variable and use the variable for imports. This lets us
change the file name in a single place every time.

#### Usage of input, output, and tourney data folders
The input data folder should only ever be touched manually. This is data that we
upload ourselves to the folder. The code itself should not write to it.

The output data folder should have data which is only generated by the pipeline.

The tourney data folder is a mix of the previous two. Sometimes, it will only
be used as an input if there are no new tournaments to scrape. Other times, 
we will include the data scraper and it will write there.

## Final thoughts
Thank you for helping keep us as organized as possible, and contributing to
USAR as a whole!
