import type { MarcFieldView, MarcRecordView } from "@/lib/api/client";

// UNIMARC's markers around the part of a title ignored in sorting (U+0098 / U+009C).
const NON_SORT_START = "\u0098";
const NON_SORT_END = "\u009c";

/** A whole record as tag / indicators / subfields, the way a cataloguer reads it. */
export function MarcRecord({ record, label }: { record: MarcRecordView; label: string }) {
  return (
    <div className="marc-record" role="table" aria-label={label}>
      <div className="marc-field" role="row">
        <span className="marc-tag" role="rowheader">
          LDR
        </span>
        <span aria-hidden="true" />
        <span role="cell" className="whitespace-pre">
          {record.leader}
        </span>
      </div>
      {record.fields.map((field, index) => (
        <MarcField key={`${field.tag}-${index}`} field={field} />
      ))}
    </div>
  );
}

/**
 * One field. [isChanged] marks it in the compare view when it differs from
 * the first record; [inTableCell] drops the row/cell roles, which the compare
 * view's own <table> already provides.
 */
export function MarcField({
  field,
  isChanged = false,
  inTableCell = false,
}: {
  field: MarcFieldView;
  isChanged?: boolean;
  inTableCell?: boolean;
}) {
  const role = (name: string) => (inTableCell ? undefined : name);
  return (
    <div className={`marc-field ${isChanged ? "marc-field-changed" : ""}`} role={role("row")}>
      <span className="marc-tag" role={role("rowheader")}>
        {field.tag}
      </span>
      {field.data != null ? (
        <>
          <span aria-hidden="true" />
          <span role={role("cell")} className="whitespace-pre-wrap break-all">
            {field.data}
          </span>
        </>
      ) : (
        <>
          <span className="marc-indicators" role={role("cell")} aria-label={`Indicadores ${indicatorText(field)}`}>
            <Indicator value={field.indicator1} />
            <Indicator value={field.indicator2} />
          </span>
          <span role={role("cell")} className="min-w-0 break-words">
            <MarcSubfields field={field} />
          </span>
        </>
      )}
    </div>
  );
}

/** The subfields of a field: "$a Os Lusíadas $f Luís de Camões". */
export function MarcSubfields({ field }: { field: MarcFieldView }) {
  return (
    <>
      {(field.subfields ?? []).map((subfield, index) => (
        <span key={index}>
          <span className="marc-subfield-code">${subfield.code}</span>
          <span className="marc-value">
            <SubfieldValue value={subfield.value} />
          </span>
          {" "}
        </span>
      ))}
    </>
  );
}

function Indicator({ value }: { value: string | null | undefined }) {
  const isBlank = !value || value === " ";
  // UNIMARC documentation writes a blank indicator as "#".
  return (
    <span className="marc-indicator" data-blank={isBlank}>
      {isBlank ? "#" : value}
    </span>
  );
}

function indicatorText(field: MarcFieldView): string {
  const show = (value: string | null | undefined) => (!value || value === " " ? "em branco" : value);
  return `${show(field.indicator1)} e ${show(field.indicator2)}`;
}

/** A subfield value, with the non-sorting part ("Os ") shown with a dotted underline. */
function SubfieldValue({ value }: { value: string }) {
  const start = value.indexOf(NON_SORT_START);
  const end = value.indexOf(NON_SORT_END);
  if (start === -1 || end <= start) return <>{value}</>;
  return (
    <>
      {value.slice(0, start)}
      <span className="marc-non-sort" title="Não conta para a ordenação">
        {value.slice(start + 1, end)}
      </span>
      {value.slice(end + 1)}
    </>
  );
}

/** A field as plain text, for comparing two records' versions of it. */
export function fieldText(field: MarcFieldView | undefined): string {
  if (!field) return "";
  if (field.data != null) return field.data;
  const subfields = (field.subfields ?? []).map((subfield) => `$${subfield.code}${subfield.value}`).join("");
  return `${field.indicator1 ?? " "}${field.indicator2 ?? " "}${subfields}`;
}
