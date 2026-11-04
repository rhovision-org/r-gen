use crate::error::RgenError;

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Verdict {
    Valid,
    Partial,
    Invalid,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MintAmounts {
    pub claimant: u64,
    pub validator: u64,
    pub total: u64,
}

/// Four quality dimensions, each 1..5, mapped to 20..100 percent; `partial` halves it.
pub fn quality_pct(quality: [u8; 4], verdict: Verdict) -> Result<u8, RgenError> {
    if quality.iter().any(|v| !(1..=5).contains(v)) {
        return Err(RgenError::Quality);
    }
    let sum: u16 = quality.iter().map(|v| u16::from(*v)).sum();
    let mut pct = (u32::from(sum) * 100 / 20) as u8;
    if verdict == Verdict::Partial {
        pct = (u32::from(pct) * 5_000 / 10_000) as u8;
    }
    Ok(pct)
}

pub fn mint_amounts(unit_mint: u64, pct: u8, rep_bps: u16) -> Result<MintAmounts, RgenError> {
    if unit_mint == 0 || pct > 100 {
        return Err(RgenError::Bps);
    }
    if !(10_000..=15_000).contains(&rep_bps) {
        return Err(RgenError::Bps);
    }
    let total = unit_mint * u64::from(pct) / 100;
    let claimant = total * 5_000 / 10_000;
    let validator = (total - claimant) * u64::from(rep_bps) / 10_000;
    Ok(MintAmounts {
        claimant,
        validator,
        total,
    })
}

pub fn reputation_bps(earned: u64) -> u16 {
    match earned {
        0..=9_999_999_999 => 10_000,
        10_000_000_000..=99_999_999_999 => 11_000,
        100_000_000_000..=999_999_999_999 => 12_500,
        _ => 15_000,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::UNIT_MINT;

    #[test]
    fn full_quality_splits_evenly() {
        let amounts = mint_amounts(UNIT_MINT, 100, 10_000).unwrap();
        assert_eq!(amounts.claimant, 5_000_000_000);
        assert_eq!(amounts.validator, 5_000_000_000);
        assert_eq!(amounts.total, UNIT_MINT);
    }

    #[test]
    fn partial_halves() {
        assert_eq!(quality_pct([4, 5, 4, 5], Verdict::Partial).unwrap(), 45);
        let amounts = mint_amounts(UNIT_MINT, 45, 10_000).unwrap();
        assert_eq!(amounts.claimant, 2_250_000_000);
        assert_eq!(amounts.validator, 2_250_000_000);
    }

    #[test]
    fn top_reputation_weight() {
        assert_eq!(reputation_bps(0), 10_000);
        assert_eq!(reputation_bps(500_000_000_000), 12_500);
        assert_eq!(reputation_bps(5_000_000_000_000), 15_000);
    }
}
