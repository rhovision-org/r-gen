#![forbid(unsafe_code)]
//! `rgen-cli`: the native client and installer signer.
//!
//! It uses the same `rgen-sdk` surface as the browser: `deploy` signs and waits for
//! finality, `manifest verify` resolves every Root key, and `keygen`/`keystore encrypt`
//! produce the local-only key material used by the devnet and testnet campaigns.

use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use clap::{Parser, Subcommand};
use rcash_chain::keystore::DevnetKeys;
use rgen_core::{payload::admin_payload, risk, token, ComponentKey, Manifest, UNIT_MINT};
use rgen_sdk::{Client, NodeReader};

const LIVE_HINTS: [&str; 4] = [
    "rhobot.net",
    "164.90.140.144",
    "167.99.43.214",
    "104.131.176.164",
];

#[derive(Debug, Parser)]
#[command(
    name = "rgen-cli",
    version,
    about = "r-gen client, installer signer and extension arithmetic"
)]
struct Cli {
    #[arg(
        long,
        env = "RGEN_NODE",
        default_value = "http://localhost:40403",
        global = true
    )]
    node: String,
    #[arg(
        long,
        env = "RGEN_MANIFEST",
        default_value = "deployments/devnet.json",
        global = true
    )]
    manifest: PathBuf,
    #[arg(
        long,
        env = "RGEN_KEYS",
        default_value = ".devnet/keys.json",
        global = true
    )]
    keys: PathBuf,
    #[arg(long, env = "RGEN_SHARD", default_value = "/root", global = true)]
    shard: String,
    #[arg(
        long,
        env = "RGEN_PHLO_LIMIT",
        default_value_t = 8_000_000,
        global = true
    )]
    phlo_limit: i64,
    #[arg(long, env = "RGEN_PHLO_PRICE", default_value_t = 1, global = true)]
    phlo_price: i64,
    /// Key name in the keys file. Defaults to the first key.
    #[arg(long, global = true)]
    key: Option<String>,
    #[arg(long, global = true)]
    json: bool,
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Check that the node answers and report its height.
    Doctor,
    /// Parse a manifest and resolve every component through the Root.
    Manifest {
        #[command(subcommand)]
        command: ManifestCommand,
    },
    /// Resolve one Root key (or all of them).
    Resolve {
        /// A Root key such as `component:claim-factory`. Omit for all nine.
        key: Option<String>,
    },
    /// Generate a fresh plaintext devnet/testnet key file (mode 0600).
    Keygen {
        #[arg(long, default_value = ".devnet/keys.json")]
        out: PathBuf,
        #[arg(
            long,
            default_value = "deployer,alice,bob,carol,dave,erin",
            value_delimiter = ','
        )]
        names: Vec<String>,
        #[arg(long)]
        fresh: bool,
    },
    /// Encrypt one key as a Web3 v3 keystore for the browser wallet.
    Keystore {
        #[command(subcommand)]
        command: KeystoreCommand,
    },
    /// Sign and submit a Rholang term, waiting for finality.
    Deploy {
        /// A term file, or `-` to read stdin.
        file: PathBuf,
        /// Operation id. Enables the write-ahead signed-body cache.
        #[arg(long)]
        op: Option<String>,
        #[arg(long, default_value = ".rgops")]
        op_cache: PathBuf,
        /// Required when the node host is a live rhobot endpoint.
        #[arg(long)]
        allow_live: bool,
    },
    /// Read the node's status for a deploy id.
    DeployStatus { deploy_id: String },
    /// Ask the node's faucet for native REV.
    Faucet {
        address: String,
        #[arg(long, default_value = "http://localhost:40403/api/v1/faucet")]
        url: String,
    },
    /// Compute S x P x E and its class (extension arithmetic, not deployed).
    RiskScore {
        #[arg(long)]
        severity: u8,
        #[arg(long)]
        probability: u8,
        #[arg(long)]
        exposure: u8,
    },
    /// Compute the KAT allocation for a quality score (extension arithmetic).
    MintAllocation {
        #[arg(long)]
        quality: u8,
        #[arg(long)]
        rep_bps: u16,
        #[arg(long, default_value_t = UNIT_MINT)]
        unit_mint: u64,
    },
    /// Print the canonical admin payload (extension arithmetic).
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

#[derive(Debug, Subcommand)]
enum ManifestCommand {
    Verify,
}

#[derive(Debug, Subcommand)]
enum KeystoreCommand {
    Encrypt {
        #[arg(long)]
        name: String,
        #[arg(long)]
        password: String,
        #[arg(long)]
        out: PathBuf,
    },
}

#[tokio::main]
async fn main() {
    let mut cli = Cli::parse();
    let command = std::mem::replace(&mut cli.command, Command::Doctor);
    match command {
        Command::Doctor => doctor(&cli.node, cli.json),
        Command::Manifest {
            command: ManifestCommand::Verify,
        } => manifest_verify(&cli).await,
        Command::Resolve { key } => resolve(&cli, key.as_deref()).await,
        Command::Keygen { out, names, fresh } => keygen(&out, &names, fresh, cli.json),
        Command::Keystore {
            command:
                KeystoreCommand::Encrypt {
                    name,
                    password,
                    out,
                },
        } => keystore_encrypt(&cli.keys, &name, &password, &out, cli.json),
        Command::Deploy {
            file,
            op,
            op_cache,
            allow_live,
        } => deploy(&cli, &file, op.as_deref(), &op_cache, allow_live).await,
        Command::DeployStatus { deploy_id } => deploy_status(&cli, &deploy_id).await,
        Command::Faucet { address, url } => faucet(&url, &address, cli.json),
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
    let reader = NodeReader::new(node);
    match reader.status() {
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

fn load_manifest(path: &Path) -> Manifest {
    match std::fs::read_to_string(path) {
        Ok(document) => match Manifest::from_json(&document) {
            Ok(manifest) => manifest,
            Err(error) => fail(&format!("{}: {error}", path.display())),
        },
        Err(_) => {
            // A deploy before the Root exists still needs a client handle. The manifest
            // is only used for resolution, which `deploy` does not perform.
            Manifest::from_json(r#"{"root_uri":"rho:id:install"}"#)
                .expect("placeholder manifest parses")
        }
    }
}

async fn manifest_verify(cli: &Cli) {
    let document = match std::fs::read_to_string(&cli.manifest) {
        Ok(document) => document,
        Err(error) => fail(&format!("{}: {error}", cli.manifest.display())),
    };
    let manifest = match Manifest::from_json(&document) {
        Ok(manifest) => manifest,
        Err(error) => fail(&error.to_string()),
    };
    let missing = manifest.missing();
    let client = Client::reader(&cli.node, manifest.clone())
        .map(|client| client.with_network(&cli.shard, cli.phlo_limit, cli.phlo_price));
    let client = match client {
        Ok(client) => client,
        Err(error) => fail(&error.to_string()),
    };
    let resolved = match client.resolve_all().await {
        Ok(resolved) => resolved,
        Err(error) => fail(&error.to_string()),
    };
    let mut mismatch = Vec::new();
    let mut entries = serde_json::Map::new();
    for (key, component) in &resolved {
        let expected = manifest.components.get(key.manifest_name());
        if let Some(expected) = expected {
            if expected != component.uri.as_str() {
                mismatch.push(serde_json::json!({
                    "key": key.key(),
                    "manifest": expected,
                    "root": component.uri.as_str()
                }));
            }
        }
        entries.insert(
            key.key().to_string(),
            serde_json::json!({"uri": component.uri.as_str(), "version": component.version}),
        );
    }
    let output = serde_json::json!({
        "node": cli.node,
        "root": manifest.root_uri.as_str(),
        "missingManifestKeys": missing.iter().map(|key| key.manifest_name()).collect::<Vec<_>>(),
        "components": entries,
        "mismatch": mismatch,
        "ok": missing.is_empty() && mismatch.is_empty()
    });
    if cli.json {
        print_json(output.clone());
    } else {
        println!("root={}", manifest.root_uri.as_str());
        for (key, component) in &resolved {
            println!(
                "{}\t{}\tv{}",
                key.key(),
                component.uri.as_str(),
                component.version
            );
        }
        if !missing.is_empty() {
            println!("manifest missing: {:?}", missing);
        }
    }
    if !output["ok"].as_bool().unwrap_or(false) {
        std::process::exit(4);
    }
}

async fn resolve(cli: &Cli, key: Option<&str>) {
    let manifest = load_manifest(&cli.manifest);
    let client = match Client::reader(&cli.node, manifest) {
        Ok(client) => client.with_network(&cli.shard, cli.phlo_limit, cli.phlo_price),
        Err(error) => fail(&error.to_string()),
    };
    let keys: Vec<ComponentKey> = match key {
        Some(key) => match ComponentKey::parse(key) {
            Ok(key) => vec![key],
            Err(error) => fail(&error.to_string()),
        },
        None => ComponentKey::ALL.to_vec(),
    };
    let mut output = serde_json::Map::new();
    for key in keys {
        match client.resolve(key).await {
            Ok(component) => {
                output.insert(
                    key.key().to_string(),
                    serde_json::json!({"uri": component.uri.as_str(), "version": component.version}),
                );
            }
            Err(error) => fail(&error.to_string()),
        }
    }
    if cli.json {
        print_json(serde_json::Value::Object(output));
    } else {
        for (key, value) in output {
            println!("{key}\t{}", value["uri"].as_str().unwrap_or("?"));
        }
    }
}

fn keygen(out: &Path, names: &[String], fresh: bool, json: bool) {
    if out.exists() && !fresh {
        fail(&format!("{} exists; pass --fresh to rotate", out.display()));
    }
    let mut keys = DevnetKeys::default();
    for name in names {
        if let Err(error) = keys.insert_generated(name.clone()) {
            fail(&error.to_string());
        }
    }
    if let Err(error) = keys.save(out) {
        fail(&error.to_string());
    }
    let entries: Vec<_> = keys
        .keys
        .values()
        .map(|key| {
            serde_json::json!({
                "name": key.name,
                "address": key.address,
                "public": key.public
            })
        })
        .collect();
    if json {
        print_json(serde_json::json!({"out": out, "keys": entries}));
    } else {
        println!("wrote {}", out.display());
        for entry in entries {
            println!("{}\t{}", entry["name"], entry["address"]);
        }
    }
}

fn keystore_encrypt(keys_path: &Path, name: &str, password: &str, out: &Path, json: bool) {
    let keys = match DevnetKeys::load(keys_path) {
        Ok(keys) => keys,
        Err(error) => fail(&format!("{}: {error}", keys_path.display())),
    };
    let key = match keys.key(name) {
        Ok(key) => key,
        Err(error) => fail(&error.to_string()),
    };
    let eth = match rcash_chain::address::eth_address_from_public_key(key.public_bytes()) {
        Ok(eth) => eth,
        Err(error) => fail(&error.to_string()),
    };
    let document = match rgen_keystore::encrypt(key.secret_bytes(), &eth, password) {
        Ok(document) => document,
        Err(error) => fail(&error),
    };
    if let Some(parent) = out.parent() {
        if let Err(error) = std::fs::create_dir_all(parent) {
            fail(&error.to_string());
        }
    }
    if let Err(error) = std::fs::write(out, format!("{document}\n")) {
        fail(&error.to_string());
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(out, std::fs::Permissions::from_mode(0o600));
    }
    let address = key.rev_address().unwrap_or_default();
    if json {
        print_json(serde_json::json!({"out": out, "address": address}));
    } else {
        println!("wrote {} for {address}", out.display());
    }
}

fn is_live(node: &str) -> bool {
    LIVE_HINTS.iter().any(|hint| node.contains(hint))
}

async fn deploy(cli: &Cli, file: &Path, op: Option<&str>, op_cache: &Path, allow_live: bool) {
    if is_live(&cli.node) && !allow_live {
        fail("this looks like a live rhobot endpoint; pass --allow-live to deploy");
    }
    let term = if file == Path::new("-") {
        let mut buffer = String::new();
        if let Err(error) = std::io::Read::read_to_string(&mut std::io::stdin(), &mut buffer) {
            fail(&error.to_string());
        }
        buffer
    } else {
        match std::fs::read_to_string(file) {
            Ok(term) => term,
            Err(error) => fail(&format!("{}: {error}", file.display())),
        }
    };
    if term.trim().is_empty() {
        fail("the term is empty");
    }
    let keys = match DevnetKeys::load(&cli.keys) {
        Ok(keys) => keys,
        Err(error) => fail(&format!("{}: {error}", cli.keys.display())),
    };
    let key_name = match cli.key.as_deref() {
        Some(name) => name.to_string(),
        None if keys.keys.contains_key("deployer") => "deployer".to_string(),
        None => match keys.keys.keys().next() {
            Some(name) => name.clone(),
            None => fail("the keys file is empty"),
        },
    };
    let key = match keys.key(&key_name) {
        Ok(key) => key,
        Err(error) => fail(&error.to_string()),
    };
    let manifest = load_manifest(&cli.manifest);
    let client = match Client::new(&cli.node, manifest, key) {
        Ok(client) => client.with_network(&cli.shard, cli.phlo_limit, cli.phlo_price),
        Err(error) => fail(&error.to_string()),
    };
    let receipt = match op {
        Some(op) => client.deploy_term_cached(&term, op, op_cache).await,
        None => client.deploy_term(&term).await,
    };
    let receipt = match receipt {
        Ok(receipt) => receipt,
        Err(error) => fail(&error.to_string()),
    };
    let reply = receipt.reply.as_ref().map(rgen_sdk::models::to_json);
    let output = serde_json::json!({
        "deployId": receipt.deploy_id,
        "finalized": receipt.finalized,
        "blockHash": receipt.block_hash,
        "blockNumber": receipt.block_number,
        "termBytes": receipt.term_bytes,
        "status": receipt.status_text,
        "key": key_name,
        "reply": reply
    });
    if cli.json {
        print_json(output);
    } else {
        println!(
            "deploy={} block={} status={}",
            receipt.deploy_id, receipt.block_number, receipt.status_text
        );
    }
}

async fn deploy_status(cli: &Cli, deploy_id: &str) {
    let manifest = load_manifest(&cli.manifest);
    let client = match Client::reader(&cli.node, manifest) {
        Ok(client) => client.with_network(&cli.shard, cli.phlo_limit, cli.phlo_price),
        Err(error) => fail(&error.to_string()),
    };
    match client.deploy_status(deploy_id).await {
        Ok(status) => {
            let output = serde_json::json!({
                "deployId": deploy_id,
                "status": status.status_text(),
                "blockNumber": status.block().map(|block| block.block_number),
                "blockHash": status.block().map(|block| block.block_hash.as_str()),
                "processed": status.is_processed(),
                "success": status.is_success()
            });
            if cli.json {
                print_json(output);
            } else {
                println!(
                    "deploy={deploy_id} status={} block={:?}",
                    status.status_text(),
                    status.block().map(|block| block.block_number)
                );
            }
        }
        Err(error) => fail(&error.to_string()),
    }
}

fn faucet(url: &str, address: &str, json: bool) {
    let body = match serde_json::to_string(address) {
        Ok(body) => body,
        Err(error) => fail(&error.to_string()),
    };
    let mut response = match ureq::post(url)
        .header("Content-Type", "application/json")
        .send(body.as_str())
    {
        Ok(response) => response,
        Err(ureq::Error::StatusCode(status)) => fail(&format!("faucet returned {status}")),
        Err(error) => fail(&error.to_string()),
    };
    let value: serde_json::Value = response
        .body_mut()
        .read_json()
        .unwrap_or(serde_json::json!({"ok": true}));
    if json {
        print_json(value);
    } else {
        println!("faucet: {value}");
    }
}

fn now_ms() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_millis() as i64)
        .unwrap_or_default()
}

#[allow(dead_code)]
fn op_id(prefix: &str) -> String {
    match rgen_sdk::new_op_id(prefix, now_ms()) {
        Ok(op) => op.as_str().to_string(),
        Err(error) => fail(&format!("{error:?}")),
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
