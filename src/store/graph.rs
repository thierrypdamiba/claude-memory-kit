use anyhow::Result;
use neo4rs::{Graph, query};

pub struct GraphStore {
    graph: Graph,
}

impl GraphStore {
    pub async fn connect() -> Result<Self> {
        let uri = std::env::var("NEO4J_URI")
            .map_err(|_| anyhow::anyhow!("NEO4J_URI not set"))?;
        if uri.is_empty() || uri.starts_with('<') {
            anyhow::bail!("NEO4J_URI is not configured");
        }
        let user = std::env::var("NEO4J_USER")
            .unwrap_or_else(|_| "neo4j".into());
        let password = std::env::var("NEO4J_PASSWORD")
            .map_err(|_| anyhow::anyhow!("NEO4J_PASSWORD not set"))?;
        if password.is_empty() || password.starts_with('<') {
            anyhow::bail!("NEO4J_PASSWORD is not configured");
        }

        let graph = Graph::new(&uri, &user, &password).await?;

        // Ensure schema exists
        graph.run(query(
            "CREATE CONSTRAINT IF NOT EXISTS \
             FOR (m:Memory) REQUIRE m.id IS UNIQUE"
        )).await?;

        graph.run(query(
            "CREATE INDEX IF NOT EXISTS \
             FOR (m:Memory) ON (m.gate)"
        )).await?;

        Ok(Self { graph })
    }

    pub async fn upsert_memory_node(
        &self,
        id: &str,
        gate: &str,
        person: Option<&str>,
        project: Option<&str>,
        content_preview: &str,
    ) -> Result<()> {
        self.graph.run(
            query(
                "MERGE (m:Memory {id: $id}) \
                 SET m.gate = $gate, m.person = $person, \
                     m.project = $project, m.preview = $preview"
            )
            .param("id", id)
            .param("gate", gate)
            .param("person", person.unwrap_or(""))
            .param("project", project.unwrap_or(""))
            .param("preview", truncate(content_preview, 200)),
        ).await?;
        Ok(())
    }

    pub async fn add_edge(
        &self,
        from_id: &str,
        to_id: &str,
        relation: &str,
    ) -> Result<()> {
        // Sanitize relation type to prevent Cypher injection —
        // only allow alphanumeric characters and underscores.
        let safe_relation: String = relation
            .chars()
            .filter(|c| c.is_alphanumeric() || *c == '_')
            .collect();
        if safe_relation.is_empty() {
            anyhow::bail!("invalid relation type: '{}'", relation);
        }
        let cypher = format!(
            "MATCH (a:Memory {{id: $from_id}}), (b:Memory {{id: $to_id}}) \
             MERGE (a)-[r:{safe_relation}]->(b) \
             SET r.created = datetime()"
        );
        self.graph.run(
            query(&cypher)
                .param("from_id", from_id)
                .param("to_id", to_id),
        ).await?;
        Ok(())
    }

    pub async fn find_related(
        &self,
        memory_id: &str,
        depth: u32,
    ) -> Result<Vec<(String, String, String)>> {
        let mut result = self.graph.execute(
            query(
                "MATCH (a:Memory {id: $id})-[r*1..2]-(b:Memory) \
                 RETURN b.id AS id, b.preview AS preview, \
                        type(r[0]) AS relation \
                 LIMIT 10"
            )
            .param("id", memory_id),
        ).await?;

        let mut related = Vec::new();
        while let Some(row) = result.next().await? {
            let id: String = row.get("id").unwrap_or_default();
            let preview: String = row.get("preview").unwrap_or_default();
            let relation: String = row.get("relation").unwrap_or_default();
            related.push((id, relation, preview));
        }
        Ok(related)
    }

    pub async fn auto_link(
        &self,
        memory_id: &str,
        person: Option<&str>,
        project: Option<&str>,
    ) -> Result<()> {
        // Link to other memories about the same person
        if let Some(person) = person {
            if !person.is_empty() {
                self.graph.run(
                    query(
                        "MATCH (a:Memory {id: $id}), \
                               (b:Memory {person: $person}) \
                         WHERE a <> b \
                         MERGE (a)-[:RELATED_TO]->(b)"
                    )
                    .param("id", memory_id)
                    .param("person", person),
                ).await?;
            }
        }

        // Link to other memories about the same project
        if let Some(project) = project {
            if !project.is_empty() {
                self.graph.run(
                    query(
                        "MATCH (a:Memory {id: $id}), \
                               (b:Memory {project: $project}) \
                         WHERE a <> b \
                         MERGE (a)-[:RELATED_TO]->(b)"
                    )
                    .param("id", memory_id)
                    .param("project", project),
                ).await?;
            }
        }
        Ok(())
    }

    pub async fn delete_node(&self, memory_id: &str) -> Result<()> {
        self.graph.run(
            query("MATCH (m:Memory {id: $id}) DETACH DELETE m")
                .param("id", memory_id),
        ).await?;
        Ok(())
    }
}

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_string()
    } else {
        let end = s.floor_char_boundary(max);
        format!("{}...", &s[..end])
    }
}
