# em-modeler
Model of the Elephant Money Protocol on the BNB-Chain  
https://elephant.money

## Usage
- Run **em_model.py** to generate the output files and plots
- EM data is input in **em_data.py** 
- Model behavior (buy, sell, etc) is set up in **setup_run.py**

## File Structure
- em_model.py is the "main" program, which executes the "daily" protocol transactions and governance strategies
- em_data.py queries the blockchain for all the relevant starting data: treasuries, LPs, Futures, Stampede, etc.
  - Note this is a slow process.  For convenience, data is stored in a pickle file for easy usage
- setup_run.py is used to manage in/out flow and growth over the course of the simulation
- bsc_classes.py contains all of the primary functions and classes used throughout the simulation.  This is where all the various "engines" are coded.
- All blockchain and protocol data is stored in "chain_data" folder.

## Notes
- To run the queries on the blockchain (in em_data.py), you must install the Moralis module and sign up for an API.  Add that variable into a file called "api.py"
  - TODO: Move everything to Web3 module...seems much faster
