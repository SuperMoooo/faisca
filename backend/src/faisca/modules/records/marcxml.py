"""MARC records in and out of XML: MARCXML (MARC21 slim) and MarcXchange (ISO 25577).

Every target's records arrive as XML: SRU returns it, and the Z39.50 client
asks YAZ for it. One parser that matches elements by local name reads both
MARCXML and MarcXchange (BnF and SUDOC send UNIMARC that way), whatever
namespace prefix the server uses.
"""

from xml.sax.saxutils import escape, quoteattr

from lxml import etree
from pymarc import Field, Indicators, Leader, Record, Subfield

from faisca.modules.records.text_cleanup import normalize_text

MARCXML_NAMESPACE = "http://www.loc.gov/MARC21/slim"

# recover: some servers send a stray control character the strict parser
# would reject; the record is still usable. no_network: never fetch a DTD.
_PARSER = etree.XMLParser(recover=True, no_network=True, resolve_entities=False, huge_tree=True)


class MarcXmlError(ValueError):
    """The XML holds no MARC record that can be read."""


def _local_name(element: etree._Element) -> str:
    tag = element.tag
    if not isinstance(tag, str):
        return ""
    return etree.QName(tag).localname


def parse_marcxml(xml_text: str | bytes) -> Record:
    """The first MARC record in [xml_text], with its text in NFC (see `normalize_text`)."""
    raw = xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text
    root = etree.fromstring(raw, _PARSER)
    if root is None:
        raise MarcXmlError("Empty or unreadable XML.")
    record_element = find_record_element(root)
    if record_element is None:
        raise MarcXmlError("No <record> element in the XML.")
    return record_from_element(record_element)


def find_record_element(root: etree._Element) -> etree._Element | None:
    """The MARC `<record>` at [root] or below it (SRU wraps records in its own elements)."""
    if _local_name(root) == "record" and _has_marc_children(root):
        return root
    for element in root.iter():
        if _local_name(element) == "record" and _has_marc_children(element):
            return element
    return None


def _has_marc_children(element: etree._Element) -> bool:
    # SRU also has <record> elements (the envelope); a MARC record is the one
    # whose children are leader / controlfield / datafield.
    return any(_local_name(child) in {"leader", "controlfield", "datafield"} for child in element)


def record_from_element(record_element: etree._Element) -> Record:
    """Builds a pymarc Record from one MARCXML/MarcXchange `<record>` element."""
    record = Record()
    leader_text = " " * 24
    for child in record_element:
        name = _local_name(child)
        if name == "leader":
            leader_text = (child.text or "").ljust(24)[:24]
        elif name == "controlfield":
            record.fields.append(
                Field(tag=child.get("tag", ""), data=normalize_text(child.text or ""))
            )
        elif name == "datafield":
            record.fields.append(_data_field_from_element(child))
    # Set after the fields: Record() overwrites leader positions 20-23 with
    # MARC21's "4500", which would be wrong for UNIMARC.
    record.leader = Leader(leader_text)
    return record


def _data_field_from_element(element: etree._Element) -> Field:
    subfields = [
        Subfield(code=sub.get("code", " "), value=normalize_text(sub.text or ""))
        for sub in element
        if _local_name(sub) == "subfield"
    ]
    indicators = Indicators(
        _indicator(element.get("ind1")),
        _indicator(element.get("ind2")),
    )
    return Field(tag=element.get("tag", ""), indicators=indicators, subfields=subfields)


def _indicator(value: str | None) -> str:
    # MARCXML writes a blank indicator as " ", some servers as "" or "#".
    if not value or value == "#":
        return " "
    return value[0]


def to_marcxml(record: Record) -> str:
    """The record as one MARCXML `<record>`; how records are stored in the cache and basket."""
    parts = [
        f'<record xmlns="{MARCXML_NAMESPACE}">',
        f"<leader>{escape(str(record.leader))}</leader>",
    ]
    for field in record.fields:
        if field.is_control_field():
            data = escape(field.data or "")
            parts.append(f"<controlfield tag={quoteattr(field.tag)}>{data}</controlfield>")
            continue
        parts.append(
            f"<datafield tag={quoteattr(field.tag)} ind1={quoteattr(field.indicator1)}"
            f" ind2={quoteattr(field.indicator2)}>"
        )
        parts.extend(
            f"<subfield code={quoteattr(sub.code)}>{escape(sub.value)}</subfield>"
            for sub in field.subfields
        )
        parts.append("</datafield>")
    parts.append("</record>")
    return "".join(parts)
