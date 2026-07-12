"""Write annotations back to DataHub after a successful build."""

from typing import Any

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.mce_builder import make_lineage_mce, get_sys_time
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.com.linkedin.pegasus2avro.dataset import DatasetProperties
from datahub.metadata._internal_schema_classes import SystemMetadataClass


def annotate_source_tables(
    gms_server: str,
    source_urns: list[str],
    model_name: str,
    model_description: str,
    target_urn: str | None = None,
) -> None:
    """Add descriptions/tags to source datasets and optionally add lineage.

    Args:
        gms_server: DataHub GMS URL (e.g. http://localhost:8080).
        source_urns: List of source dataset URNs.
        model_name: Name of the generated model.
        model_description: Description of the generated model.
        target_urn: Optional URN of the downstream model dataset.
    """
    emitter = DatahubRestEmitter(gms_server=gms_server)

    for urn in source_urns:
        # Emit a DatasetProperties MCP to add description
        props = DatasetProperties(
            description=f"Source for generated model: {model_name} — {model_description}",
        )
        mcp = MetadataChangeProposalWrapper(
            entityType="DATASET",
            changeType="UPSERT",
            entityUrn=urn,
            aspectName="datasetProperties",
            aspect=props,
            systemMetadata=SystemMetadataClass(lastObserved=get_sys_time(), runId="model-forge-writeback"),
        )
        emitter.emit_mcp(mcp)
        print(f"  Annotated {urn} with model reference", flush=True)

    # Add lineage if target URN provided
    if target_urn and source_urns:
        lineage_mce = make_lineage_mce(
            upstream_urns=source_urns,
            downstream_urn=target_urn,
            lineage_type="TRANSFORMED",
        )
        emitter.emit_mce(lineage_mce)
        print(f"  Added lineage: {len(source_urns)} sources -> {target_urn}", flush=True)

    emitter.close()
