import logging
import random
from typing import Optional, List

from src import settings
from src.benchmark_readers.aida_conll_benchmark_reader import AidaConllBenchmarkReader
from src.benchmark_readers.nif_benchmark_reader import NifBenchmarkReader
from src.benchmark_readers.our_jsonl_benchmark_reader import OurJsonlBenchmarkReader
from src.benchmark_readers.simple_jsonl_benchmark_reader import SimpleJsonlBenchmarkReader
from src.benchmark_readers.tagme_benchmark_reader import TagmeBenchmarkReader
from src.benchmark_readers.xml_benchmark_reader import XMLBenchmarkReader
from src.evaluation.benchmark import BenchmarkFormat, Benchmark
from src.models.entity_database import EntityDatabase

logger = logging.getLogger("main." + __name__.split(".")[-1])

random.seed(42)


def get_benchmark_iterator(benchmark_name: str,
                           from_json_file: Optional[bool] = True,
                           benchmark_files: Optional[List[str]] = None,
                           benchmark_format: Optional[BenchmarkFormat] = None):
    if benchmark_files:
        if benchmark_format == BenchmarkFormat.NIF.value:
            logger.info("Load mappings for NIF benchmark reader...")
            entity_db = EntityDatabase()
            entity_db.load_wikipedia_wikidata_mapping()
            entity_db.load_redirects()
            logger.info("-> Mappings loaded.")
            benchmark_iterator = NifBenchmarkReader(entity_db, benchmark_files[0])
        elif benchmark_format == BenchmarkFormat.AIDA_CONLL.value:
            logger.info("Load mappings for AIDA CoNLL benchmark reader...")
            entity_db = EntityDatabase()
            entity_db.load_wikipedia_wikidata_mapping()
            entity_db.load_redirects()
            logger.info("-> Mappings loaded.")
            benchmark_iterator = AidaConllBenchmarkReader(entity_db, benchmark_files[0])
        elif benchmark_format == BenchmarkFormat.SIMPLE_JSONL.value:
            logger.info("Load mappings for Simple JSONL benchmark reader...")
            entity_db = EntityDatabase()
            entity_db.load_wikipedia_wikidata_mapping()
            entity_db.load_redirects()
            logger.info("-> Mappings loaded.")
            benchmark_iterator = SimpleJsonlBenchmarkReader(entity_db, benchmark_files[0])
        elif benchmark_format == BenchmarkFormat.XML.value:
            if len(benchmark_files) == 1:
                raise IndexError("The XML benchmark reader needs the XML file and the directory with raw texts "
                                 "as input, but only one file was provided.")
            logger.info("Load mappings for XML benchmark reader...")
            entity_db = EntityDatabase()
            entity_db.load_wikipedia_wikidata_mapping()
            entity_db.load_redirects()
            logger.info("-> Mappings loaded.")
            benchmark_iterator = XMLBenchmarkReader(entity_db, benchmark_files[0], benchmark_files[1])
        elif benchmark_format == BenchmarkFormat.tagme.value:
            if len(benchmark_files) == 1:
                raise IndexError("The TagMe benchmark reader needs the annotation file and the text snippet file "
                                 "as input, but only one file was provided.")
            logger.info("Load mappings for TagMe benchmark reader...")
            entity_db = EntityDatabase()
            entity_db.load_wikipedia_wikidata_mapping()
            entity_db.load_redirects()
            entity_db.load_wikipedia_id2wikipedia_title()
            logger.info("-> Mappings loaded.")
            benchmark_iterator = TagmeBenchmarkReader(entity_db, benchmark_files[0], benchmark_files[1])
        else:
            # Per default, assume OUR_JSONL format
            benchmark_iterator = OurJsonlBenchmarkReader(benchmark_files[0])
    elif from_json_file or benchmark_name in [Benchmark.WIKI_EX.value, Benchmark.NEWSCRAWL.value]:
        benchmark_filename = settings.BENCHMARK_DIR + benchmark_name + ".benchmark.jsonl"
        benchmark_iterator = OurJsonlBenchmarkReader(benchmark_filename)
    elif benchmark_name in [Benchmark.AIDA_CONLL.value, Benchmark.AIDA_CONLL_TRAIN.value,
                            Benchmark.AIDA_CONLL_DEV.value, Benchmark.AIDA_CONLL_TEST.value]:
        logger.info("Load mappings for benchmark reader...")
        entity_db = EntityDatabase()
        entity_db.load_wikipedia_wikidata_mapping()
        entity_db.load_redirects()
        logger.info("-> Mappings loaded.")
        benchmark_iterator = AidaConllBenchmarkReader(entity_db, settings.AIDA_CONLL_BENCHMARK_FILE, benchmark_name)
    else:
        raise ValueError("%s is not a known benchmark." % benchmark_name)
    return benchmark_iterator
