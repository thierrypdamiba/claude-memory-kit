use chrono::Utc;
use crate::types::{DecayClass, Memory};

/// Compute a decay score for a memory (0.0 = should archive, 1.0 = very alive)
pub fn compute_decay_score(memory: &Memory) -> f64 {
    let recency = recency_factor(memory);
    let frequency = frequency_factor(memory);
    recency * frequency
}

fn recency_factor(memory: &Memory) -> f64 {
    let half_life = match memory.decay_class.half_life_days() {
        Some(h) => h,
        None => return 1.0, // Never decays
    };

    let days_since = (Utc::now() - memory.last_accessed)
        .num_hours() as f64 / 24.0;

    // Exponential decay: score = 0.5^(days/half_life)
    (0.5_f64).powf(days_since / half_life)
}

fn frequency_factor(memory: &Memory) -> f64 {
    // log(access_count + 1) normalized so 1 access = 1.0
    (memory.access_count as f64 + 1.0).ln() / (2.0_f64).ln()
}

/// Check if a memory should be flagged as fading (score < 0.1)
pub fn is_fading(memory: &Memory) -> bool {
    match memory.decay_class {
        DecayClass::Never => false,
        _ => compute_decay_score(memory) < 0.1,
    }
}
