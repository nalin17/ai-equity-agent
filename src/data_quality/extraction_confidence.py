"""Extraction confidence (architecture 4A, rule 4).

Extraction confidence says how sure the system is that it READ a document correctly - for
example, that a headline is about a given company. It says nothing about whether that company
is a good investment. The two are stored and reported separately, and extraction confidence
never flows into investment confidence.

The levels are evidence classes, not probabilities: no probability has been measured, so none
is invented. This is the single place the vocabulary is defined.
"""
from enum import StrEnum


class ExtractionConfidence(StrEnum):
    """How a company was found: in a news article (rule nw-entity-1, strongest first) or in a SEBI
    release (rule sb-entity-1). For macro events (rules me-types-1, me-releases-1, me-sebi-1): how the
    event's type was read."""
    NAME_IN_HEADLINE_AND_LINK = "name_in_headline_and_link"   # one company, named in both
    NAME_IN_A_LIST = "name_in_a_list"                         # one item of a list of names in the headline
    NAME_IN_HEADLINE_ONLY = "name_in_headline_only"
    NAME_IN_LINK_ONLY = "name_in_link_only"
    SEVERAL_COMPANIES_NAMED = "several_companies_named"
    NO_NAME_FOUND = "no_name_found"                           # the article stays unassigned
    REGISTERED_NAME_IN_TITLE = "registered_name_in_title"     # a SEBI release names the company
    ISSUER_DOCUMENT_CODE = "issuer_document_code"             # the central bank's own document code in the link
    ISSUER_TITLE = "issuer_title"                             # the central bank's own fixed title
    STATISTICS_RELEASE = "statistics_release"                 # a new period first appeared in an official series
    REGULATOR_SECTION = "regulator_section"                   # the regulator's own section in the link
    OWNER_DECLARED = "owner_declared"                         # declared by the owner, citing a public source
    NOT_TYPED = "not_typed"                                   # no rule gives this item a registered type
