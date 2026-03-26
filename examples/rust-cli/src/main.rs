// main.rs — main module.
//
// exports: none
// used_by: none
// rules:   none
// agent:   claude-haiku-4-5-20251001 | unknown | 2026-03-27 | unknown | initial CodeDNA annotation pass

//! main.rs — CLI entry point: reads CSV file, parses and prints formatted report.
//!
//! exports: main()
//! used_by: none
//! rules:   exits with code 1 on missing arg or file read error — no panic unwrap in main.
//! agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation

mod formatter;
mod parser;

use std::env;
use std::fs;
use std::process;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: codedna-example <file>");
        process::exit(1);
    }

    let path = &args[1];
    let source = fs::read_to_string(path).unwrap_or_else(|e| {
        eprintln!("Error reading {}: {}", path, e);
        process::exit(1);
    });

    let records = parser::parse_csv(&source);
    let report = formatter::format_report(&records);
    println!("{}", report);
}
