"""Sample catalogue results for `MOCK_RESPONSES=true`: no network, no database.

Two records of the same book: a native UNIMARC one from PORBASE and a MARC21
one from the Library of Congress (converted, so the compare view and the
"original MARC21" tab have something to show). Every search answers with
them, and PORBASE "timed out" once, so a client can draw partial results.
"""

from pathlib import Path

from faisca.core.config import Settings
from faisca.core.errors import NotFoundError
from faisca.modules.catalogues.record_ids import make_record_id
from faisca.modules.catalogues.schemas import (
    CatalogueSearchResponse,
    RecordDetail,
    RecordGroup,
    RecordVariant,
    SearchQuery,
    TargetOutcome,
    TargetSearchStatus,
)
from faisca.modules.catalogues.service import CatalogueService, FoundRecord
from faisca.modules.records.public import (
    CatalogueRecord,
    MarcFormat,
    read_catalogue_record,
    work_key,
)
from faisca.modules.targets.public import CatalogueProtocol, CatalogueTarget, TargetsConfig

SAMPLES_DIR = Path(__file__).parent / "samples"


def _read_sample(filename: str) -> str:
    """A sample MARCXML record shipped next to this module."""
    return (SAMPLES_DIR / filename).read_text(encoding="utf-8")


SAMPLE_UNIMARC = _read_sample("sample_unimarc.xml")

SAMPLE_MARC21 = _read_sample("sample_marc21.xml")

SAMPLE_TARGETS = {
    "porbase": (
        "PORBASE — Base Nacional de Dados Bibliográficos",
        "PT",
        MarcFormat.UNIMARC,
        SAMPLE_UNIMARC,
    ),
    "loc": ("Library of Congress", "US", MarcFormat.MARC21, SAMPLE_MARC21),
}


def _sample_target(target_id: str) -> CatalogueTarget:
    name, country, marc_format, _ = SAMPLE_TARGETS[target_id]
    return CatalogueTarget(
        id=target_id,
        name=name,
        country=country,
        protocol=CatalogueProtocol.Z3950,
        format=marc_format,
        host="example.invalid",
        port=210,
        database="sample",
    )


def sample_records() -> list[FoundRecord]:
    """The two sample records, built anew on every call."""
    found: list[FoundRecord] = []
    for target_id, (_, _, marc_format, marcxml) in SAMPLE_TARGETS.items():
        record: CatalogueRecord = read_catalogue_record(marcxml, marc_format)
        record_id = make_record_id(target_id, record.control_number, marcxml)
        found.append(
            FoundRecord(record_id=record_id, target=_sample_target(target_id), record=record)
        )
    return found


class CatalogueMockService(CatalogueService):
    """Answers like CatalogueService, from the samples, without network or database."""

    def __init__(self, config: TargetsConfig, settings: Settings) -> None:
        self.config = config
        self.settings = settings

    async def search(self, query: SearchQuery) -> CatalogueSearchResponse:
        """The two samples as one group; LoC answered, PORBASE timed out once."""
        records = sample_records()
        summaries = [found.summary() for found in records]
        return CatalogueSearchResponse(
            query=query,
            groups=[RecordGroup(key=work_key(summaries[0].description), records=summaries)],
            record_count=len(summaries),
            targets=[
                TargetOutcome(
                    target_id="porbase",
                    target_name=SAMPLE_TARGETS["porbase"][0],
                    status=TargetSearchStatus.OK,
                    hit_count=1829,
                    returned_count=1,
                    elapsed_ms=840,
                ),
                TargetOutcome(
                    target_id="loc",
                    target_name=SAMPLE_TARGETS["loc"][0],
                    status=TargetSearchStatus.OK,
                    hit_count=401,
                    returned_count=1,
                    elapsed_ms=1210,
                ),
                TargetOutcome(
                    target_id="blx",
                    target_name="Rede de Bibliotecas de Lisboa",
                    status=TargetSearchStatus.TIMED_OUT,
                    elapsed_ms=25000,
                    error="Sem resposta dentro do tempo limite.",
                ),
            ],
        )

    async def find_record(self, record_id: str) -> FoundRecord:
        """A sample by id, or NotFoundError, so a client can test both."""
        for found in sample_records():
            if found.record_id == record_id:
                return found
        raise NotFoundError(f"O registo {record_id} não existe.")

    async def get_record_detail(self, record_id: str) -> RecordDetail:
        """The sample's detail, without touching a session."""
        found = await self.find_record(record_id)
        return RecordDetail(
            summary=found.summary(),
            unimarc=found.record.unimarc_view(),
            original=found.record.original_view(),
        )

    async def get_record_file(self, record_id: str, variant: RecordVariant) -> tuple[str, bytes]:
        """The sample as ISO 2709."""
        found = await self.find_record(record_id)
        if variant is RecordVariant.ORIGINAL:
            return (
                f"{record_id}-{found.record.source_format.value}.mrc",
                found.record.original_iso2709(),
            )
        return f"{record_id}-unimarc.mrc", found.record.unimarc_iso2709()
