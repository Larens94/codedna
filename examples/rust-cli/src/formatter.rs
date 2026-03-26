// formatter.rs — formatter module.
//
// exports: format_report | format_summary
// used_by: none
// rules:   none
// agent:   claude-haiku-4-5-20251001 | unknown | 2026-03-27 | unknown | initial CodeDNA annotation pass

//! formatter.rs — Formats Vec<Record> as aligned table or summary string.
//!
//! exports: format_report(records: &[Record]) -> String | format_summary(records, count_field) -> String
//! used_by: main.rs → main
//! rules:   format_summary silently skips records where count_field is non-numeric —
//!          no error is returned, total may be lower than expected.
//! agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation

use crate::parser::Record;

pub fn format_report(records: &[Record]) -> String {
    if records.is_empty() {
        return "No records found.".to_string();
    }

    let headers: Vec<String> = records[0].fields.keys().cloned().collect();
    let col_widths: Vec<usize> = headers
        .iter()
        .map(|h| {
            records
                .iter()
                .map(|r| r.fields.get(h).map(|v| v.len()).unwrap_or(0))
                .max()
                .unwrap_or(0)
                .max(h.len())
        })
        .collect();

    let mut lines = vec![];
    let header_row = headers
        .iter()
        .zip(&col_widths)
        .map(|(h, w)| format!("{:<width$}", h, width = w))
        .collect::<Vec<_>>()
        .join(" | ");
    lines.push(header_row);
    lines.push(col_widths.iter().map(|w| "-".repeat(*w)).collect::<Vec<_>>().join("-+-"));

    for record in records {
        let row = headers
            .iter()
            .zip(&col_widths)
            .map(|(h, w)| format!("{:<width$}", record.fields.get(h).unwrap_or(&String::new()), width = w))
            .collect::<Vec<_>>()
            .join(" | ");
        lines.push(row);
    }

    lines.join("\n")
}

pub fn format_summary(records: &[Record], count_field: &str) -> String {
    let total = records
        .iter()
        .filter_map(|r| r.fields.get(count_field)?.parse::<f64>().ok())
        .sum::<f64>();
    format!("Total {}: {:.2} ({} records)", count_field, total, records.len())
}
