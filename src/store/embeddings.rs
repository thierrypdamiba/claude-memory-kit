use anyhow::Result;
use qdrant_client::qdrant::{
    CreateCollectionBuilder, Distance, PointStruct,
    SearchPointsBuilder, UpsertPointsBuilder, VectorParamsBuilder,
    DeletePointsBuilder, PointsIdsList,
    points_selector::PointsSelectorOneOf,
};
use qdrant_client::Qdrant;

const COLLECTION: &str = "claude_memories";
const VECTOR_SIZE: u64 = 384;

pub struct EmbeddingStore {
    client: Qdrant,
    model: fastembed::TextEmbedding,
}

impl EmbeddingStore {
    pub async fn connect() -> Result<Self> {
        let url = std::env::var("QDRANT_URL")
            .map_err(|_| anyhow::anyhow!("QDRANT_URL not set"))?;
        if url.is_empty() || url.starts_with('<') {
            anyhow::bail!("QDRANT_URL is not configured");
        }
        let api_key = std::env::var("QDRANT_API_KEY")
            .map_err(|_| anyhow::anyhow!("QDRANT_API_KEY not set"))?;
        if api_key.is_empty() || api_key.starts_with('<') {
            anyhow::bail!("QDRANT_API_KEY is not configured");
        }

        let client = Qdrant::from_url(&url)
            .api_key(api_key)
            .build()?;

        if !client.collection_exists(COLLECTION).await? {
            client.create_collection(
                CreateCollectionBuilder::new(COLLECTION)
                    .vectors_config(
                        VectorParamsBuilder::new(VECTOR_SIZE, Distance::Cosine),
                    ),
            ).await?;
            tracing::info!("created qdrant collection: {}", COLLECTION);
        }

        let model = fastembed::TextEmbedding::try_new(
            fastembed::InitOptions::new(fastembed::EmbeddingModel::AllMiniLML6V2)
                .with_show_download_progress(false),
        )?;

        Ok(Self { client, model })
    }

    pub async fn embed_and_store(
        &self,
        memory_id: &str,
        content: &str,
        person: Option<&str>,
        project: Option<&str>,
    ) -> Result<()> {
        let embeddings = self.model.embed(vec![content], None)?;
        let vector = embeddings.into_iter().next()
            .ok_or_else(|| anyhow::anyhow!("embedding failed"))?;

        let mut payload = std::collections::HashMap::<String, qdrant_client::qdrant::Value>::new();
        payload.insert("memory_id".into(), memory_id.to_string().into());
        payload.insert("content".into(), content.to_string().into());
        if let Some(p) = person {
            payload.insert("person".into(), p.to_string().into());
        }
        if let Some(p) = project {
            payload.insert("project".into(), p.to_string().into());
        }

        // Qdrant requires UUID or integer point IDs
        let point_id = uuid::Uuid::new_v4().to_string();
        let point = PointStruct::new(point_id, vector, payload);

        self.client.upsert_points(
            UpsertPointsBuilder::new(COLLECTION, vec![point])
        ).await?;
        Ok(())
    }

    pub async fn search_similar(
        &self,
        query: &str,
        limit: u64,
    ) -> Result<Vec<(String, f32)>> {
        let embeddings = self.model.embed(vec![query], None)?;
        let vector = embeddings.into_iter().next()
            .ok_or_else(|| anyhow::anyhow!("embedding failed"))?;

        let results = self.client.search_points(
            SearchPointsBuilder::new(COLLECTION, vector, limit)
                .with_payload(true),
        ).await?;

        let mut out = Vec::new();
        for point in results.result {
            let mem_id = point.payload.get("memory_id")
                .and_then(|v| match &v.kind {
                    Some(qdrant_client::qdrant::value::Kind::StringValue(s)) => Some(s.clone()),
                    _ => None,
                })
                .unwrap_or_default();
            out.push((mem_id, point.score));
        }
        Ok(out)
    }

    pub async fn delete_point(&self, memory_id: &str) -> Result<()> {
        use qdrant_client::qdrant::{Condition, Filter};
        self.client.delete_points(
            DeletePointsBuilder::new(COLLECTION)
                .points(Filter::must([
                    Condition::matches("memory_id", memory_id.to_string()),
                ])),
        ).await?;
        Ok(())
    }
}
