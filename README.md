# Entity Linking

## Docker Instructions
Get the code, and build and start the container:

    git clone git@github.com:ad-freiburg/wiki_entity_linker.git .
    docker build -t wiki-entity-linker .
    docker run -it -v <data_directory>:/data wiki-entity-linker

where `<data_directory>` is the directory that either already contains the necessary data files
or where you want to store the generated data files.

Unless otherwise noted, all the following commands should be run inside the docker container.

## Data Generation
For linking entities in a text or evaluating the output of a linker, our system needs information about entities and mention texts,
e.g. entity labels, aliases, popularity scores, types, the frequency with which a mention is linked to a certain article in Wikipedia, etc.
This information is stored in and read from several files.
This section describes how you can easily generate all the necessary data files.

Before however, make sure to set the `DATA_DIR` variable in the Makefile to your `<data_directory>`
(within the docker container, `DATA_DIR` is automatically set to `/data/`).
In `src/settings.py` set the `EXTRACTED_WIKIPEDIA_DUMP_NAME` variable to `"enwiki-latest-extracted.jsonl"`
if this is not already the case.

If you do not already have access to the necessary data files, you can generate all files in two simple steps.
Otherwise, e.g. if you have run these two steps before, you can skip the following steps and jump straight to *Usage* section.

As a first step, either run

    make download_entity_types

to download the `entity-types.tsv` file and move it to the required destination
**OR** if you want to build it yourself, outside the docker container run

    make build_entity_types

This will run the steps described in detail in `wikidata-types/README.md`.
Roughly, it clones the QLever code from Github and builds the QLever docker image if no such image exists on the machine already.
It then builds a QLever index with corrections from `wikidata-types/corrections.txt`
and issues a query for all Wikidata entities and all their types from a given whitelist of types (listed in `wikidata-types/types.txt`).
The resulting file is moved to `<data_directory>/wikidata-mappings/entity-types.tsv` .
This build step requires about 25 GB of RAM and 100 GB of disk space and assumes that there is a
running QLever instance for Wikidata under the URL specified by the variable `API_WIKIDATA` in the `Makefile`
(by default, this is set to https://qlever.cs.uni-freiburg.de/api/wikidata).
This step can be run in parallel to the following setup step.

For the second step, in the docker container run

    make setup
    
This will generate all remaining necessary data files.
The setup includes downloading and extracting the latest Wikipedia dump and will take several hours (< 10h).

NOTE: This will overwrite existing Wikidata and Wikipedia mappings in your `<data_directory>` so make sure this is
what you want to do.

Data generation has to be done only once unless you want to update the generated data files to a more recent Wikipedia
or Wikidata version.

## Usage

### Link Wikipedia Dump
To link an entire Wikipedia dump using our best system run
    
    make link_wiki
    
This uses our link-text-linker which links entities based on Wikipedia hyperlinks,
our popular-entities linker which links remaining entities based on their Wikidata sitelink count with special rules for demonyms,
and our coreference linker which uses type and gender information of previously linked entities and dependency parse information.

NOTE: Linking the entire Wikipedia dump will take several hours.
You can adjust the number of processes used for linking via the Makefile variable `NUM_LINKER_PROCESSES`.

The output file (per default `<data_directory>/wikipedia_dump_files/enwiki-latest-linked.jsonl`)
will contain one json object representing a linked Wikipedia article per line.

#### Link an Additional Recent Wikipedia Dump
If you want to link a more recent Wikipedia dump than the one that was downloaded during the data generation step,
first make sure your existing Wikipedia dump files are not being overwritten by either renaming your existing
`<data_directory>/wikipedia_dump_files/enwiki-latest-pages-articles-multistream.xml.bz2`,
`<data_directory>/wikipedia_dump_files/enwiki-latest-extracted.jsonl`
and if you already linked a Wikipedia dump
`<data_directory>/wikipedia_dump_files/enwiki-latest-linked.jsonl`
files or by adjusting the `WIKI_DUMP`, `EXTRACTED_WIKI_DUMP` and `LINKED_WIKI_ARTICLES` variables in the Makefile.

Then run

    make download_wiki extract_wiki link_wiki

which will download, extract and link the most recent Wikipedia dump.

#### Create QLever Text Files
If you want to use the linked Wikipedia dump for full-text search in QLever as described
[here](https://github.com/ad-freiburg/qlever/blob/master/docs/sparql_plus_text.md) run

    python3 create_qlever_text_files.py <input_file> <output_prefix>

where `<input_file>` is the linked Wikipedia dump file
(usually `<data_directory>/wikipedia_dump_files/enwiki-latest-linked.jsonl`)
and `<output_prefix>` is the prefix for the generated output files.
This will generate two files `<output_prefix>.wordsfile.tsv` and `<output_prefix>.docsfile.tsv`
which can then be used as input for a SPARQL + Text instance of QLever.

### Link Benchmark Articles
If you're using docker and want to persistently store the benchmark linking results,
set the `EVALUATION_RESULTS_DIR` variable in the Makefile to a mounted directory, e.g. `/data/evaluation_results/`.

To link all benchmarks specified in the Makefile's `BENCHMARK_NAMES` variable
using all linking systems specified in the Makefile's `LINKING_SYSTEMS` variable run

    make link_benchmarks

The linking results are written to subdirectories in the directory specified in the Makefile's `EVALUATION_RESULTS_DIR` variable.
You can examine or adjust each system's exact linking arguments in the Makefile's `link_benchmark` target if needed.

If you don't want to use the Makefile for linking, e.g. if you want to link only a single benchmark with a
single specified linker configuration, use the script `link_benchmark_entities.py`, e.g.

    python3 link_benchmark_entities.py <linking_result_jsonl_file> popular_entities 15 --link_linker link-text-linker -coref entity -b wiki-ex

Use the `-h` option for more information on the command line arguments.
The linking result will be written to `<linking_result_jsonl_file> ` with one WikipediaArticle json object per line.

NOTE: The linking results for some systems like Neural-EL, Wikifier and Ambiverse need to be created separately
and stored at a path that can then be passed to `link_benchmark_entities.py` as linker argument.
See the READMEs in the `neural-el` or `wikifier` directories for more information.
For other systems like Spacy or Explosion you first need to train the respective linker (explained later in this README).


### Evaluate Linked Benchmark Articles

To evaluate the linking results in the subdirectories of the directory `EVALUATION_RESULTS_DIR`
for benchmarks specified in the Makefile's `BENCHMARK_NAMES` variable run

    make evaluate_linked_benchmarks

The evaluation results will be written to the same subdirectories in `EVALUATION_RESULTS_DIR`. 

This will create the files necessary for the `evaluation-webapp` and print precision, recall and F1 scores.
To show the evaluation results in the webapp, follow the instructions in `evaluation-webapp`.

If you don't want to use the Makefile for the evaluation, e.g. if you want to evaluate only a single linking result file,
use the script `evaluate_linked_entities.py`:

    python3 evaluate_linked_entities.py <linking_result_jsonl_file>


### Initialize and Train Spacy Entity Linker

1. Generate word vectors:

       python3 create_entity_word_vectors.py 0
2. Create the knowledge base:

       python3 create_knowledge_base_wikipedia.py
3. Train the entity linker:

       python3 train_spacy_entity_linker.py <linker_name> <n_batches> wikipedia

## Notes

If you want to be able to run coreference with the Stanford CoreNLP coreference resolution system, make sure to setup Stanford CoreNLP by running

    ./setup_stanford_coref.sh
