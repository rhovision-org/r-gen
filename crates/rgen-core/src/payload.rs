/// Canonical admin payload. The chain hashes this string with blake2b256 and verifies DER
/// secp256k1 signatures over the digest. Arguments are flat strings and integers.
pub fn admin_payload(domain: &str, nonce: i64, action: &str, args: &[String]) -> String {
    format!(
        "rgen:admin:v1|{}|{}|{}|{}",
        domain,
        nonce,
        action,
        args.join(",")
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn payload_is_stable() {
        let payload = admin_payload("root", 7, "rotate", &["key".into(), "1".into()]);
        assert_eq!(payload, "rgen:admin:v1|root|7|rotate|key,1");
    }

    #[test]
    fn empty_args_keep_the_separator() {
        assert_eq!(
            admin_payload("root", 1, "freeze", &[]),
            "rgen:admin:v1|root|1|freeze|"
        );
    }
}
