# em-modeler
Model of the Elephant Money Protocol on BSC

## Usage
- Run **em_model.py** to generate the output files and plots
- EM data is input in **em_data.py** 
- Model behavior (buy, sell, etc) is set up in **setup_run.py**

## Notes
- To run the queries on the blockchain (in em_data.py), you must install the Moralis module and sign up for an API.  Add that variable into a file called "api.py"
- Otherwise the token and LP data is stored in the pickle file and that can be used for repeated runs
- All blockchain and protocol data is stored in "chain_data" folder.
- Use the latest pickle file (point to in em_data.py)
- trend.csv tracks the historical data (from the pickle files) in a csv
- delta_*.csv tracks the change over time (recent and full)

## Major TODOs:
1. Update Stampede Engine to v6
2. Add Trumpet and new burn mechanics
3. Add NFTs
