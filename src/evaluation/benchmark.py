import os

from enum import Enum
from src import settings


class Benchmark(Enum):
    WIKI_EX = "wiki-ex"
    AIDA_CONLL = "aida-conll"
    AIDA_CONLL_TRAIN = "aida-conll-train"
    AIDA_CONLL_DEV = "aida-conll-dev"
    AIDA_CONLL_TEST = "aida-conll-test"
    ACE = "ace"
    ACE_ORIGINAL = "ace-original"
    MSNBC_UPDATED = "msnbc-updated"
    MSNBC_ORIGINAL = "msnbc"
    WIKIPEDIA = "wikipedia"
    NEWSCRAWL = "newscrawl"


class BenchmarkFormat(Enum):
    OURS_JSONL = "ours"
    NIF = "nif"
    AIDA_CONLL = "aida-conll"
    SIMPLE_JSONL = "simple-jsonl"
    XML = "xml"
    TAGME = "tagme"


def get_available_benchmarks():
    benchmark_names = []
    for filename in sorted(os.listdir(settings.BENCHMARK_DIR)):
        if filename.endswith(".benchmark.jsonl"):
            benchmark_name = filename.replace(".benchmark.jsonl", "")
            benchmark_names.append(benchmark_name)
    return benchmark_names
