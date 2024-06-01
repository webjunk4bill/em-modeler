# em-modeler
Model of the Elephant Money Protocol on the BNB-Chain  
https://elephant.money

Updated 2024-06-01

## Usage
- *dune_extractor.py*
  - used to pull historical data about the protocol from dune.  
  - API key is required for this.
  - Data is used to create ML models to predict future deposits and withdrawals
  - Data is stored in a pickle for retrieval by the main program
- *em_data.py* 
  - queries the blockchain to set up the latest balances for the various treasuries and LPs
  - It also queries CMC to get the latest prices for BTC and BNB
- *setup_run.py* 
  - used to set up growth assumptions and a few other items for the model
- *em_model.py*
  - This is the main simulator.  It runs on daily basis.
  - Outputs various parameters about the protocol into *output_time.csv*
  - Generates plots (can be modified in *plotting.py*)

## File Structure
- bsc_classes.py contains all of the primary functions and classes used throughout the simulation.  This is where all the various "engines" are coded.
- All blockchain and protocol data is stored in "chain_data" folder.
- *api.py* - place key personal information in this file
  - **dune_api** Dune API for Dune queries
  - **cmc_key** CMC key for price queries
  - **bsc_url** Custom BSC endpoint or the mainnet (I recommend grove)

## Notes
- All functions are up to date as of May 2024, including the new Turbines
- Market buy/sell of trunk is ignored for now, but protocol usage is captured
