import os
import csv
import argparse
import pandas as pd

from scrape_vocab import scrape_vocab
from global_var import *

def parse_args():
    parser = argparse.ArgumentParser(description='Scrape vocabularies from an online dictionary.')

    # positional argument
    parser.add_argument('input', type=str,
                        help='Path to input csv file.')
    parser.add_argument('output', type=str,
                        help='Path of output csv file.')
    parser.add_argument('error', type=str,
                        help='Path of file storing elements when having error.')
    
    # optional arguments
    parser.add_argument('--vocabulary-store', type=str, default=None,
                        help='Path to vocabulary store.')
    # this optional will used for future features
    # parser.add_argument('-d', '--dictionary', type=str, default='cambridge',
    #                     help='Dictionary where to get vocabulary (cambridge or oxford)')

    # parse
    return parser.parse_args()


if __name__ == '__main__':
    # parse arguments
    args = parse_args()
    
    # crawling
    vocabs = pd.read_csv(args.input, names=INPUT_HEADER)

    if os.path.exists(args.vocabulary_store):
        new_vocabs, latest_vocabs = scrape_vocab(vocabs, args.vocabulary_store)
    new_vocabs, latest_vocabs = scrape_vocab(vocabs)

    # save output
    if isinstance(new_vocabs, tuple):
        new_vocabs, incorrect_vocabs = new_vocabs
    else:
        incorrect_vocabs = None

    new_vocabs.to_csv(args.output, index=False, header=False, quoting=csv.QUOTE_ALL)
    if incorrect_vocabs is not None:
        incorrect_vocabs.to_csv(args.error, index=False, header=False, quoting=csv.QUOTE_ALL)

    # update latest vocabulary store
    if args.vocabulary_store is not None:
        latest_vocabs.to_csv(args.vocabulary_store, header=False, index=False, quoting=csv.QUOTE_ALL)