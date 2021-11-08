import argparse

from typing import Set
from src import settings
from src.helpers.entity_database_reader import EntityDatabaseReader


def extract_relevant_types(coarse_types: Set[str]):
    """
    Extract all types of an entity up until two levels below the highest level
    (which is usually the class 'entity') or until a type that exists in the
    coarse types list, whichever comes first in the type hierarchy.
    """
    entity_to_relevant_types = {}
    with open(settings.QID_TO_ALL_TYPES_FILE, "r") as file:
        for line in file:
            line = line.strip('\n')
            lst = line.split("\t")
            if len(lst) < 2:
                continue
            entity_id = lst[0]
            highest_level = int(lst[-1].split(":")[0])
            max_level = highest_level
            coarse_type_found = False
            for el in lst[1:]:
                test_lst = el.split(":")
                if len(test_lst) > 2:
                    continue
                level, type_id = el.split(":")
                level = int(level)
                if level > min(max_level, 3):
                    break
                if type_id in coarse_types:
                    coarse_type_found = True
                    max_level = level
                elif not coarse_type_found and level > highest_level - 2:
                    max_level = level
                if entity_id not in entity_to_relevant_types:
                    entity_to_relevant_types[entity_id] = []
                entity_to_relevant_types[entity_id].append(type_id)
    return entity_to_relevant_types


def main(args):
    coarse_types = EntityDatabaseReader.get_coarse_types()
    print("Building mapping...")
    entity_to_relevant_types = extract_relevant_types(coarse_types)
    print("Writing mapping...")
    with open(args.output_file, "w", encoding="utf8") as outfile:
        for entity_id, types in entity_to_relevant_types.items():
            outfile.write("%s\t" % entity_id)
            for i, cl in enumerate(types):
                outfile.write("%s" % cl)
                if i < len(types) - 1:
                    outfile.write(";")
            outfile.write("\n")
    print("Wrote mapping to %s" % args.output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=__doc__)

    parser.add_argument("-o", "--output_file", type=str, default=settings.QID_TO_RELEVANT_TYPES_FILE,
                        help="Output file.")

    main(parser.parse_args())