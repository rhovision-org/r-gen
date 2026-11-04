#![forbid(unsafe_code)]
//! `rgen-cli`: local domain arithmetic plus a read-only node doctor.

use clap::{Parser, Subcommand};
use rgen_core::{payload::admin_payload, risk, token, UNIT_MINT};
use rgen_sdk::Client;

#[derive(Debug, Parser)]
#[command(
    name = "rgen-cli",
    version,
    about = "RGen domain arithmetic and node reader"
)]
struct Cli {
    #[arg(long, env = "RGEN_NODE", default_value = "http://localhost:40403")]
    node: String,
    #[arg(long)]
    json: bool,
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Check that the node answers and report its height.
    Doctor,
    /// Compute S x P x E and its class.
    RiskScore {
        #[arg(long)]
        severity: u8,
        #[arg(long)]
        probability: u8,
        #[arg(long)]
        exposure: u8,
    },
    /// Compute the KAT allocation for a quality score and reputation weight.
    MintAllocation {
        #[arg(long)]
        quality: u8,
        #[arg(long)]
        rep_bps: u16,
        #[arg(long, default_value_t = UNIT_MINT)]
        unit_mint: u64,
    },
    /// Print the canonical admin payload that must be hashed and signed.
    AdminPayload {
        #[arg(long)]
        domain: String,
        #[arg(long)]
        nonce: i64,
        #[arg(long)]
        action: String,
        #[arg(long, default_value = "")]
        args: String,
    },
}

fn main() {
    let cli = Cli::parse();
    match cli.command {
        Command::Doctor => doctor(&cli.node, cli.json),
        Command::RiskScore {
            severity,
            probability,
            exposure,
        } => {
            let score = match risk::risk_score(severity, probability, exposure) {
                Ok(score) => score,
                Err(error) => fail(&error.to_string()),
            };
            let class = match risk::risk_class(score) {
                Ok(class) => class,
                Err(error) => fail(&error.to_string()),
            };
            let gates = risk::risk_gates(class);
            if cli.json {
                print_json(serde_json::json!({
                    "score": score,
                    "class": class.as_str(),
                    "validatorLevel": gates.validator_level,
                    "approverLevel": gates.approver_level,
                    "needsOracle": gates.needs_oracle
                }));
            } else {
                println!(
                    "score={score} class={} validatorLevel={} approverLevel={} needsOracle={}",
                    class.as_str(),
                    gates.validator_level,
                    gates.approver_level,
                    gates.needs_oracle
                );
            }
        }
        Command::MintAllocation {
            quality,
            rep_bps,
            unit_mint,
        } => {
            let pct = match token::quality_pct([quality; 4], token::Verdict::Valid) {
                Ok(pct) => pct,
                Err(error) => fail(&error.to_string()),
            };
            let amounts = match token::mint_amounts(unit_mint, pct, rep_bps) {
                Ok(amounts) => amounts,
                Err(error) => fail(&error.to_string()),
            };
            if cli.json {
                print_json(serde_json::json!({
                    "qualityPct": pct,
                    "claimant": amounts.claimant,
                    "validator": amounts.validator,
                    "total": amounts.total
                }));
            } else {
                println!(
                    "qualityPct={pct} claimant={} validator={} total={}",
                    amounts.claimant, amounts.validator, amounts.total
                );
            }
        }
        Command::AdminPayload {
            domain,
            nonce,
            action,
            args,
        } => {
            let args: Vec<String> = if args.is_empty() {
                Vec::new()
            } else {
                args.split(',').map(str::to_string).collect()
            };
            println!("{}", admin_payload(&domain, nonce, &action, &args));
        }
    }
}

fn doctor(node: &str, json: bool) {
    let client = Client::new(node);
    match client.status() {
        Ok(status) => {
            if json {
                print_json(status);
            } else {
                let height = status
                    .get("latestBlockNumber")
                    .map(ToString::to_string)
                    .unwrap_or_else(|| "?".into());
                let network = status
                    .get("networkId")
                    .and_then(|v| v.as_str())
                    .unwrap_or("?");
                println!("node={node} network={network} height={height}");
            }
        }
        Err(error) => fail(&error.to_string()),
    }
}

fn print_json(value: serde_json::Value) {
    match serde_json::to_string_pretty(&value) {
        Ok(text) => println!("{text}"),
        Err(error) => fail(&error.to_string()),
    }
}

fn fail(message: &str) -> ! {
    eprintln!("rgen-cli: {message}");
    std::process::exit(3)
}
