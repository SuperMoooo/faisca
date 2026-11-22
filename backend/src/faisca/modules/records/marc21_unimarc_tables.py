"""Code tables for the MARC21 → UNIMARC conversion.

Sources: the Library of Congress "UNIMARC to MARC 21 Conversion
Specifications" (read in reverse) and the IFLA UNIMARC Bibliographic manual,
3rd edition with updates, Appendix C (relator codes) and fields 100/102/105.
"""

# MARC21 relator code (or English term) → UNIMARC relator code (Appendix C).
RELATOR_CODES: dict[str, str] = {
    "aut": "070",
    "author": "070",
    "edt": "340",
    "editor": "340",
    "ed": "340",
    "trl": "730",
    "translator": "730",
    "tr": "730",
    "ill": "440",
    "illustrator": "440",
    "aui": "080",
    "author of introduction": "080",
    "aft": "075",
    "author of afterword": "075",
    "com": "220",
    "compiler": "220",
    "comp": "220",
    "ctb": "205",
    "contributor": "205",
    "cmp": "230",
    "composer": "230",
    "lyr": "520",
    "lyricist": "520",
    "pht": "600",
    "photographer": "600",
    "pbl": "650",
    "publisher": "650",
    "prf": "590",
    "performer": "590",
    "drt": "300",
    "director": "300",
    "ann": "020",
    "annotator": "020",
    "wpr": "070",
    "adp": "010",
    "adapter": "010",
    "cre": "070",
    "creator": "070",
    "ive": "460",
    "interviewee": "460",
    "ivr": "470",
    "interviewer": "470",
    "prt": "610",
    "printer": "610",
    "scl": "700",
    "art": "040",
    "artist": "040",
    "cwt": "212",
    "commentator for written text": "212",
    "dte": "280",
    "dedicatee": "280",
    "rev": "675",
    "reviewer": "675",
    "ths": "727",
    "thesis advisor": "727",
}

# Relators that make a name an "alternative responsibility" (UNIMARC 701/711)
# rather than a "secondary responsibility" (702/712): co-authors.
AUTHOR_RELATORS = {"070", "071", "072"}
DEFAULT_PRIMARY_RELATOR = "070"

# MARC21 country codes (008/15-17) → ISO 3166-1 alpha-2 (UNIMARC 102 $a).
# US states (xxu, nyu, cau, …) and the UK nations end in "u" and "k".
COUNTRY_CODES: dict[str, str] = {
    "po": "PT",
    "sp": "ES",
    "fr": "FR",
    "gw": "DE",
    "it": "IT",
    "bl": "BR",
    "xxu": "US",
    "xxk": "GB",
    "enk": "GB",
    "stk": "GB",
    "wlk": "GB",
    "nik": "GB",
    "xxc": "CA",
    "mx": "MX",
    "ag": "AR",
    "cl": "CL",
    "ck": "CO",
    "pe": "PE",
    "ve": "VE",
    "uy": "UY",
    "be": "BE",
    "ne": "NL",
    "sz": "CH",
    "au": "AT",
    "ie": "IE",
    "dk": "DK",
    "sw": "SE",
    "no": "NO",
    "fi": "FI",
    "pl": "PL",
    "xr": "CZ",
    "hu": "HU",
    "gr": "GR",
    "ru": "RU",
    "ja": "JP",
    "cc": "CN",
    "ii": "IN",
    "at": "AU",
    "nz": "NZ",
    "sa": "ZA",
    "ao": "AO",
    "mz": "MZ",
    "cv": "CV",
    "pg": "GW",
    "sf": "ST",
    "em": "TL",
    "mh": "MO",
    "lu": "LU",
}

# 008/06 type of date → UNIMARC 100 $a/8 type of publication date.
PUBLICATION_DATE_TYPES: dict[str, str] = {
    "s": "d",  # single known date
    "m": "g",  # multiple dates, spanning more than a year
    "r": "e",  # reprint / reproduction
    "t": "h",  # publication and copyright dates
    "q": "f",  # questionable date
    "n": "u",  # unknown
    "e": "j",  # detailed date
    "p": "i",  # distribution / production
    "i": "g",  # inclusive dates of a collection
    "k": "g",
    "c": "a",  # continuing resource, currently published
    "d": "b",  # continuing resource, ceased
    "u": "c",  # continuing resource, status unknown
    "|": "u",
}

# 008/22 target audience → UNIMARC 100 $a/17.
TARGET_AUDIENCES: dict[str, str] = {
    "a": "b",
    "b": "c",
    "c": "d",
    "d": "e",
    "e": "k",
    "f": "k",
    "g": "m",
    "j": "a",
    " ": "u",
    "|": "u",
}

# 008/28 government publication → UNIMARC 100 $a/20.
GOVERNMENT_PUBLICATIONS: dict[str, str] = {
    "f": "a",
    "s": "b",
    "c": "e",
    "l": "d",
    "m": "e",
    "i": "f",
    "z": "h",
    "o": "h",
    "u": "u",
    " ": "y",
    "|": "y",
}

# Leader/06 type of record: MARC21 → UNIMARC.
RECORD_TYPES: dict[str, str] = {
    "a": "a",
    "t": "b",
    "c": "c",
    "d": "d",
    "e": "e",
    "f": "f",
    "g": "g",
    "i": "i",
    "j": "j",
    "k": "k",
    "m": "l",
    "o": "m",
    "p": "m",
    "r": "r",
}

# Leader/17 encoding level: MARC21 → UNIMARC (blank = full, 1-3 = sublevels).
ENCODING_LEVELS: dict[str, str] = {
    " ": " ",
    "1": "1",
    "2": "1",
    "4": "1",
    "3": "3",
    "5": "3",
    "7": "3",
    "8": "2",
    "u": "3",
    "z": "3",
}

# 008/18-21 illustrations → UNIMARC 105 $a/0-3.
ILLUSTRATION_CODES: dict[str, str] = {
    "a": "a",
    "b": "b",
    "c": "c",
    "d": "d",
    "e": "e",
    "f": "f",
    "g": "g",
    "h": "h",
    "i": "i",
    "j": "j",
    "k": "k",
    "l": "l",
    "m": "m",
    "o": "a",  # photographs: UNIMARC has no own code, they are illustrations
    "p": "o",  # illuminations
}

# 008/24-27 nature of contents → UNIMARC 105 $a/4-7.
CONTENT_CODES: dict[str, str] = {
    "a": "d",
    "b": "a",
    "c": "b",
    "d": "e",
    "e": "f",
    "i": "c",
    "l": "n",
    "m": "m",
    "n": "r",
    "p": "j",
    "r": "g",
    "s": "i",
    "t": "p",
    "u": "l",
    "w": "n",
    "z": "s",
    "6": "t",
}

# 008/33 literary form → UNIMARC 105 $a/11.
LITERARY_FORMS: dict[str, str] = {
    "0": "y",
    "1": "a",
    "d": "b",
    "e": "c",
    "f": "a",
    "h": "d",
    "i": "e",
    "j": "f",
    "m": "z",
    "p": "g",
    "s": "h",
    "u": "y",
    "|": "y",
}

# 008/34 biography → UNIMARC 105 $a/12.
BIOGRAPHY_CODES: dict[str, str] = {"a": "a", "b": "b", "c": "c", "d": "d"}

# MARC21 5XX notes → UNIMARC 3XX. Notes not listed become 300 (general note).
NOTE_TAGS: dict[str, str] = {
    "500": "300",
    "501": "300",
    "502": "328",
    "504": "320",
    "505": "327",
    "506": "371",
    "508": "323",
    "510": "321",
    "511": "323",
    "516": "336",
    "518": "300",
    "520": "330",
    "521": "333",
    "530": "300",
    "533": "325",
    "534": "324",
    "538": "337",
    "540": "371",
    "546": "302",
    "586": "334",
}

# MARC21 linking entries → UNIMARC 4XX.
LINKING_TAGS: dict[str, str] = {
    "765": "454",  # original language entry → translation of
    "767": "453",  # translation entry → translated as
    "775": "451",  # other edition → other edition in the same medium
    "776": "452",  # additional physical form → edition in a different medium
    "780": "430",  # preceding entry → continues
    "785": "440",  # succeeding entry → continued by
    "773": "461",  # host item → set
}

# MARC21 246 second indicator → UNIMARC variant-title tag.
VARIANT_TITLE_TAGS: dict[str, str] = {
    "1": "510",  # parallel title
    "4": "512",  # cover title
    "5": "513",  # added title-page title
    "8": "516",  # spine title
}
