//! parser.rs — CSV parser: reads raw text into Vec<Record> with named fields.
//!
//! exports: parse_csv(source: &str) -> Vec<Record> | filter_records<'a>(records, key, value) -> Vec<&Record>
//! used_by: main.rs → main | formatter.rs → format_report
//! rules:   parse_csv uses the first line as headers — empty or missing header line returns empty vec.
//!          field count mismatch is silently padded with empty strings, never panics.
//! agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation

use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct Record {
    pub fields: HashMap<String, String>,
}

pub fn parse_csv(source: &str) -> Vec<Record> {
    let mut lines = source.lines();
    let headers: Vec<String> = match lines.next() {
        Some(h) => h.split(',').map(|s| s.trim().to_string()).collect(),
        None => return vec![],
    };

    lines
        .filter(|l| !l.trim().is_empty())
        .map(|line| {
            let values: Vec<&str> = line.split(',').collect();
            let fields = headers
                .iter()
                .enumerate()
                .map(|(i, h)| (h.clone(), values.get(i).unwrap_or(&"").trim().to_string()))
                .collect();
            Record { fields }
        })
        .collect()
}

pub fn filter_records<'a>(records: &'a [Record], key: &str, value: &str) -> Vec<&'a Record> {
    records
        .iter()
        .filter(|r| r.fields.get(key).map(|v| v == value).unwrap_or(false))
        .collect()
}
