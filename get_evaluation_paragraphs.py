import sys
import random

from src.wikipedia_corpus import WikipediaCorpus


N_PARAGRAPHS_PER_ARTICLE = 3
EVAL_START_TAG = "<START>"
EVAL_END_TAG = "<END>"


if __name__ == "__main__":
    print_text = sys.argv[1] == "text"

    random.seed(31072020)
    articles = list(WikipediaCorpus.development_articles())
    random.shuffle(articles)
    for a_i, article in enumerate(articles):
        text = article.text
        paragraphs = text.split("\n\n")
        n_paragraphs = len(paragraphs)
        if len(paragraphs[-1].strip()) == 0:
            n_paragraphs = n_paragraphs - 1
        if n_paragraphs - 1 <= N_PARAGRAPHS_PER_ARTICLE:
            eval_begin_paragraph = 1
        else:
            eval_begin_paragraph = random.randint(1, n_paragraphs - N_PARAGRAPHS_PER_ARTICLE)
        eval_end_paragraph = min(len(paragraphs), eval_begin_paragraph + N_PARAGRAPHS_PER_ARTICLE)
        paragraph_lengths = [len(paragraph) for paragraph in paragraphs]
        start = sum(paragraph_lengths[:eval_begin_paragraph]) + 2 * eval_begin_paragraph
        end = start + sum(paragraph_lengths[eval_begin_paragraph:eval_end_paragraph]) + \
            2 * (eval_end_paragraph - eval_begin_paragraph - 1)
        article.set_evaluation_span(start, end)
        if print_text:
            preceding = text[:start]
            eval_text = text[start:end]
            after = text[end:]
            print("**** ARTICLE #%i: %s (%s) *****" % (a_i + 1, article.title, article.url))
            print(preceding + EVAL_START_TAG + eval_text + EVAL_END_TAG + after)
        else:
            print(article.to_json())
