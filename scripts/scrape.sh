#!/bin/bash

# Check if the user provided an argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <input_file>"
    exit 1
fi

# Assign the input file to a variable
INPUT_FILE=$1

# Define other file paths
OUTPUT_FILE="data/running/new_words.csv"
ERROR_FILE="data/running/error_words.csv"
VOCAB_STORE="data/running/vocab_store.csv"

# Run the Python script with the provided input file
export PYTHONPATH=.
python src/scrape.py "$INPUT_FILE" "$OUTPUT_FILE" "$ERROR_FILE" --vocabulary-store "$VOCAB_STORE"