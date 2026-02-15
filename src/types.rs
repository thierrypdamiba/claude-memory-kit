use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum Gate {
    Behavioral,
    Relational,
    Epistemic,
    Promissory,
}

impl Gate {
    pub fn as_str(&self) -> &str {
        match self {
            Gate::Behavioral => "behavioral",
            Gate::Relational => "relational",
            Gate::Epistemic => "epistemic",
            Gate::Promissory => "promissory",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "behavioral" => Some(Gate::Behavioral),
            "relational" => Some(Gate::Relational),
            "epistemic" => Some(Gate::Epistemic),
            "promissory" => Some(Gate::Promissory),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum DecayClass {
    Slow,
    Moderate,
    Fast,
    Never,
}

impl DecayClass {
    pub fn half_life_days(&self) -> Option<f64> {
        match self {
            DecayClass::Never => None,
            DecayClass::Slow => Some(180.0),
            DecayClass::Moderate => Some(90.0),
            DecayClass::Fast => Some(30.0),
        }
    }

    pub fn from_gate(gate: &Gate) -> Self {
        match gate {
            Gate::Promissory => DecayClass::Never,
            Gate::Relational => DecayClass::Slow,
            Gate::Epistemic => DecayClass::Moderate,
            Gate::Behavioral => DecayClass::Fast,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Memory {
    pub id: String,
    pub created: DateTime<Utc>,
    pub gate: Gate,
    pub person: Option<String>,
    pub project: Option<String>,
    pub confidence: f64,
    pub last_accessed: DateTime<Utc>,
    pub access_count: u32,
    pub decay_class: DecayClass,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JournalEntry {
    pub timestamp: DateTime<Utc>,
    pub gate: Gate,
    pub content: String,
    pub person: Option<String>,
    pub project: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdentityCard {
    pub person: Option<String>,
    pub project: Option<String>,
    pub content: String,
    pub last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub memory: Memory,
    pub score: f64,
    pub source: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractedMemory {
    pub gate: String,
    pub content: String,
    pub person: Option<String>,
    pub project: Option<String>,
}
