"Simple translation of words."

from icecream import ic

import csv


class Translation:
    "Simple translation of words from one language to another."

    def __init__(self, translation_csv_file, source=None, target=None):
        """The CSV file must have one column per language.
        The header of each column specifies the name of the language.
        """
        with open(translation_csv_file) as infile:
            self.terms = list(csv.DictReader(infile))
        self.source = source or tuple(self.terms[0].keys())[0]
        self.target = target or tuple(self.terms[0].keys())[1]
        self.set_translation(self.source, self.target)

    def __str__(self):
        return f"{self.__class__.__name__} {self.source} -> {self.target}"

    @property
    def languages(self):
        return tuple(self.terms[0].keys())

    def set_translation(self, source, target):
        if source not in self.terms[0]:
            raise ValueError(f"language 'source' not in the translation data.")
        if target not in self.terms[0]:
            raise ValueError(f"language 'target' not in the translation data.")
        self.translation = dict()
        for term in self.terms:
            self.translation[term[source]] = term[target]
            self.translation[term[source].lower()] = term[target].lower()
            self.translation[term[source].upper()] = term[target].upper()
            self.translation[term[source].capitalize()] = term[target].capitalize()

    def __call__(self, term):
        return self.translation.get(term, term)


if __name__ == "__main__":
    t = Translation("translation.csv")
    ic(str(t))
    ic(t.languages)
    for term in ["item", "section"]:
        ic(term, t(term))