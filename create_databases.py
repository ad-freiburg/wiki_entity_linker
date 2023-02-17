import argparse
import pickle
import time
import dbm
from typing import Optional
from urllib.parse import unquote

import log
import sys
from enum import Enum


WIKI_URL_PREFIX = "https://en.wikipedia.org/wiki/"


class StorageFormat(Enum):
    SINGLE_VAL = "single_value"
    MULTI_VALS = "multiple_values"
    MULTI_VALS_TS = "multiple_values_tab_separated"
    MULTI_VALS_SS = "multiple_values_semicolon_separated"


class ValueProcessingMethod(Enum):
    NAME_FROM_URL = "name_from_url"


def read_from_pkl(filename, separator=","):
    logger.info(f"Reading from file {filename} ...")
    start = time.time()
    with open(filename, "rb") as f:
        d = pickle.load(f)
        if StorageFormat.MULTI_VALS:
            new_d = {}
            for key, value in d.items():
                if type(value) is list:
                    string = ""
                    for i, v in enumerate(value):
                        string += v
                        if i < len(value) - 1:
                            string += separator
                    new_d[key] = string
                else:
                    new_d[key] = value
            d = new_d
    logger.info(f"Done. Took {time.time() - start} s")
    return d


def read_from_tsv(filename, storage_format=StorageFormat.SINGLE_VAL, processing_method=None, inverse=False,
                  separator=","):
    logger.info(f"Reading from file {filename} ...")
    start = time.time()
    d = {}
    with open(filename, "r", encoding="utf8") as f:
        for line in f:
            lst = line.strip("\n").split("\t")
            if storage_format == StorageFormat.SINGLE_VAL:
                if inverse:
                    key = process(lst[1], processing_method)
                    d[key] = lst[0]
                else:
                    d[lst[0]] = process(lst[1], processing_method)
            elif storage_format == StorageFormat.MULTI_VALS:
                if inverse:
                    curr_key = process(lst[1], processing_method)
                    curr_val = lst[0]
                    if curr_key in d:
                        prev_val = d[curr_key]
                        d[curr_key] = prev_val + separator + curr_val
                    else:
                        d[curr_key] = curr_val
                else:
                    curr_key = lst[0]
                    curr_val = process(lst[1], processing_method)
                    if curr_key in d:
                        prev_val = d[curr_key]
                        d[curr_key] = prev_val + separator + curr_val
                    else:
                        d[curr_key] = curr_val
            elif storage_format in [StorageFormat.MULTI_VALS_SS, StorageFormat.MULTI_VALS_TS]:
                value_separator = ";" if storage_format == StorageFormat.MULTI_VALS_SS else "\t"
                if inverse:
                    keys = lst[1].split(value_separator)
                    for key in keys:
                        key = process(key, processing_method)
                        if key in d:
                            prev_val = d[key]
                            d[key] = prev_val + separator + lst[0]
                        else:
                            d[key] = lst[0]
                else:
                    vals = [process(v, processing_method) for v in lst[1].split(value_separator)]
                    val = separator.join(vals)
                    d[lst[0]] = val

    logger.info(f"Done. Took {time.time() - start} s")
    return d


def process(value: str, method: Optional[ValueProcessingMethod] = None) -> str:
    if method == ValueProcessingMethod.NAME_FROM_URL:
        # Can't use rfind("/") here, because some entity names contain "/", e.g.
        # https://www.wikidata.org/wiki/Q51402020
        value = value[len(WIKI_URL_PREFIX):]
        value = unquote(value)
        value = value.replace('_', ' ')
    return value


def read_from_dbm(filename):
    logger.info(f"Reading from database file {filename} ...")
    start = time.time()
    db = dbm.open(filename, "r")
    logger.info(f"Done. Took {time.time() - start} s")
    return db


def write_to_dbm(d, filename):
    logger.info(f"Writing database to file {filename} ...")
    start = time.time()
    count = 0
    with dbm.open(filename, "nf") as db:
        # Store the dictionary data in the database
        for key, value in d.items():
            db[key] = value
            count += 1
            if count % 100000 == 0:
                logger.info(f"Wrote {count} items of {len(d)}.")
    logger.info(f"Done. Took {time.time() - start} s")


def main(args):
    output_file = args.output_file if args.output_file else args.input_file[:args.input_file.rfind(".")] + ".db"

    storage_format = StorageFormat(args.format)
    processing_method = ValueProcessingMethod(args.processing_method) if args.processing_method else None

    if args.input_file.endswith(".pkl"):
        dictionary = read_from_pkl(args.input_file)
    else:
        dictionary = read_from_tsv(args.input_file, storage_format, processing_method, inverse=args.inverse)

    write_to_dbm(dictionary, output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("input_file", type=str,
                        help="Input file to transform to DB. Either TSV or PKL file.")
    parser.add_argument("-o", "--output_file", type=str,
                        help="File name of the generated DB. Default: Input filename with suffix .db")
    parser.add_argument("-f", "--format", type=str, choices=[f.value for f in StorageFormat],
                        default=StorageFormat.SINGLE_VAL, help="Storage format of the input file")
    parser.add_argument("-m", "--processing_method", type=str, choices=[m.value for m in ValueProcessingMethod],
                        default=None, help="Processing method that will be applied to each value in the database.")
    parser.add_argument("-i", "--inverse", action="store_true",
                        help="Use the original keys (left-most element) as values, and the values as keys.")

    logger = log.setup_logger(sys.argv[0])
    logger.debug(' '.join(sys.argv))

    main(parser.parse_args())
