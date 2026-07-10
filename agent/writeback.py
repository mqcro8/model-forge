"""Write annotations back to DataHub after a successful build."""

from typing import Any

from datahub.emitter.mce_builder import make_dataset_urn
from datahub.emitter.rest_emitter import DatahubRestEmitter


def annotate_source_tables(
    gms_server: str,
    source_urns: list[str],
    model_name: str,
    model_description: str,
) -> None:
    """Add a description/tag to source datasets noting the new derived model.

    Args:
        gms_server: DataHub GMS URL (e.g. http://localhost:8080).
        source_urns: List of source dataset URNs.
        model_name: Name of the generated model.
        model_description: Description of the generated model.
    """
    emitter = DatahubRestEmitter(gms_server=gms_server)

    for urn in source_urns:
        # TODO: Build and emit a MetadataChangeProposal that adds:
        #   - A description on the dataset noting the new model
        #   - A glossary term or tag referencing the model
        #   - Optionally, an explicit add_lineage() call
        raise NotImplementedError("Write-back not yet implemented")
