# Add a Benchmark
You can easily add a benchmark if you have a benchmark file that is in one of the following formats:

- our JSONL format
- NLP Interchange Format (NIF)
- IOB-based format used by Hoffart et al. for their AIDA/CoNLL benchmark
- a very simple JSONL format

To add a benchmark, simply run

    python3 add_benchmark.py <benchmark_name> -bfile <benchmark_file> -bformat <ours|nif|aida-conll|simple-jsonl>

This converts the `<benchmark_file>` into our JSONL format (if it is not in this format already), annotates ground
 truth labels with their Wikidata label and Wikidata types as given in
 `<data_directory>/wikidata_mappings/entity-types.tsv` and writes the result to the file
 `benchmarks/<benchmark_name>.benchmark.jsonl`. Additionally, a file `benchmarks/<benchmark_name>.metadata.jsonl` is
 created that contains metadata information such as a benchmark description and the benchmark name that will be
 displayed in the evaluation webapp. The description and displayed name can be specified using the `-desc` and
 `-dname` arguments.

If your benchmark is not in one of the supported formats, you can either convert it into one of those formats
 yourself or write your own benchmark reader, as explained in section
 [Writing a Custom Benchmark Reader](#writing-a-custom-benchmark-reader).

## Benchmark Formats

This section describes the three file formats that can be used as input to the `add_benchmark.py` script.

#### Our JSONL Format

Our JSONL format is described in detail [here](our_jsonl_format.md).

#### NIF
The NIF format for the purpose of entity linking is explained in detail in the
[GERBIL Wiki](https://github.com/dice-group/gerbil/wiki/How-to-generate-a-NIF-dataset).

Your benchmark file should look something like this:

    @prefix itsrdf: <http://www.w3.org/2005/11/its/rdf#> .
    @prefix nif: <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    
    <http://www.aksw.org/gerbil/NifWebService/request_0#char=0,87> a nif:Context,
        nif:OffsetBasedString ;
    nif:beginIndex "0"^^xsd:nonNegativeInteger ;
    nif:endIndex "87"^^xsd:nonNegativeInteger ;
    nif:isString "Angelina, her father Jon, and her partner Brad never played together in the same movie." .
    
    <http://www.aksw.org/gerbil/NifWebService/request_0#offset_42_46> a nif:OffsetBasedString,
            nif:Phrase ;
        nif:anchorOf "Brad" ;
        nif:beginIndex "42"^^xsd:nonNegativeInteger ;
        nif:endIndex "46"^^xsd:nonNegativeInteger ;
        nif:referenceContext <http://www.aksw.org/gerbil/NifWebService/request_0#char=0,87> ;
        itsrdf:taIdentRef <https://en.wikipedia.org/wiki/Brad_Pitt> .

Note that in ELEVANT
- entity identifiers can be from Wikidata, Wikipedia or DBpedia
- `<benchmark_file>` can be the path to a single NIF file that contains all benchmark articles or the path to a
 directory that contains multiple such NIF files
 
The NIF benchmark reader is implemented [here](../src/benchmark_readers/nif_benchmark_reader.py).

#### AIDA/CoNLL IOB Format
The format should be as follows:
- Each document starts with a line that starts with the string `-DOCSTART-`
- Each following line represents a single token, sentences are separated by an empty line

Lines with tabs are tokens the are part of a mention, where
- column 1 is the token.
- column 2 is either "B" (beginning of a mention), "I" (continuation of a mention) or "O" (outside of a mention). The
 O can be omitted.
- column 3 is the full mention, *but its content is not used by our benchmark reader*.
- column 4 is the corresponding YAGO2 entity OR `--NME--`, denoting an unknown entity. *We only use this column to
 check whether its content is `--NME--`*.
- column 5 is the corresponding Wikipedia URL of the entity. *In ELEVANT, this can also be a Wikidata or DBpedia URL.*
- column 6 is the corresponding Wikipedia ID of the entity, *but its content is not used by our benchmark reader*.
- column 7 is the corresponding Freebase mid, *but its content is not used by our benchmark reader*.

Your benchmark file should look something like this:

    -DOCSTART- (1 EU)
    EU	B	EU	--NME--
    rejects
    German	B	German	Germany	http://en.wikipedia.org/wiki/Germany	11867	/m/0345h
    call
    to
    boycott
    British	B	British	United_Kingdom	http://en.wikipedia.org/wiki/United_Kingdom	31717	/m/07ssc
    lamb
    .
    
    Peter	B	Peter Blackburn	--NME--
    Blackburn	I	Peter Blackburn	--NME--

The AIDA-CoNLL benchmark reader is implemented [here](../src/benchmark_readers/aida_conll_benchmark_reader.py).

#### Simple JSONL Format
The benchmark file should contain one line per benchmark article, where each line is a json object with the
 following keys:
- `text`: The text of the benchmark article
- `title` (*optional*): The title of the benchmark article
- `labels`: The ground truth labels for an article. An array of objects with the keys
    - `entity_reference`: The reference to the predicted entity in one of the knowledge bases [Wikidata, Wikipedia
    , DBpedia]. The reference is either a complete link to the entity (e.g.
    "https://en.wikipedia.org/wiki/Angelina_Jolie") or just the Wikidata QID / Wikipedia title / DBpedia title. Note
    however, if no complete link is given the knowledge base is inferred from the format of the entity reference and
    predicted Wikipedia titles that match the regular expression `Q[0-9]+` will be interpreted as Wikidata QIDs.
    - `start_char`: The character offset of the start of the label (including) within the article text
    - `end_char`: The character offset of the end of the label (excluding) within the article text

Your benchmark file should look something like this:

    {"text": "Angelina, her father Jon, and her partner Brad never played together in the same movie.", "title": "Some Title", "labels": [{"entity_reference": "Angelina Jolie", "start_char": 0, "end_char": 8}, {"entity_reference": "Jon Voight", "start_char": 21, "end_char": 24}, {"entity_reference": "Brad Pitt", "start_char": 42, "end_char": 46}]}
    {"text": "Heidi and her husband Seal live in Vegas.", "title": "Some Title", "labels": [{"entity_reference": "Heidi Klum", "start_char": 0, "end_char": 5}, {"entity_reference": "Seal", "start_char": 22, "end_char": 26}, {"entity_reference": "Las Vegas", "start_char": 35, "end_char": 40}]}

`<benchmark_file>` can be the path to a single JSONL file that contains all benchmark articles or the path to a
 directory that contains multiple such JSONL files.

The Simple JSONL benchmark reader is implemented [here](../src/benchmark_readers/simple_jsonl_benchmark_reader.py).


## Writing a Custom Benchmark Reader
As an alternative to converting your benchmark into one of the formats mentioned above, you can write your own
 benchmark reader, such that you can use your benchmark file with the `add_benchmark.py` script directly.
 This requires the following steps:

1) Implement a benchmark reader in `src/benchmark_readers/` and implement a method `article_iterator` that takes a
 benchmark path and yields an Iterator over `src.models.article.Article` objects where each `Article` object represents
 a benchmark article with at the very least some unique (within the benchmark) article ID, article title, article
 text and groundtruth labels. Use the `src.benchmark_readers.simple_jsonl_benchmark_reader.SimpleJsonlBenchmarkReader
 `as a template for how to write a benchmark reader. You can use the
 `src.utils.knowledge_base_mapper.KnowledgeBaseMapper`'s `get_wikidata_qid` method to convert Wikipedia or DBpedia
 benchmark entities to Wikidata. Use the `src.utils.nested_groundtruth_handler.NestedGroundtruthHandler`'s
 `assign_parent_and_child_ids` method if your benchmark may contain nested groundtruth labels.

2) Add your custom benchmark reader name to the `src.evaluation.benchmark.BenchmarkFormat` enum, e.g.
 `MY_FORMAT = "my_format"`.

3) Create a class `MyFormatExampleReader` in `src/evaluation/examples_generator.py`. Use the `SimpleJsonlExampleReader`
 class as a template.

4) Add an elif-branch in the `src.evaluation.examples_generator.get_example_generator` function under the
 `if benchmark_file` branch , e.g.

        elif benchmark_format == BenchmarkFormat.MY_FORMAT.value:
            logger.info("Load mappings for My Format example generator...")
            entity_db = EntityDatabase()
            entity_db.load_wikipedia_wikidata_mapping()
            entity_db.load_redirects()
            logger.info("-> Mappings loaded.")
            example_generator = MyFormatExampleReader(entity_db, benchmark_file)

You can now add benchmarks in your format by running

    python3 add_benchmark.py <benchmark_name> -bfile <benchmark_file> -bformat my_format