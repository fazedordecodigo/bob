from __future__ import annotations

import yaml
from yaml.composer import ComposerError

_MERGE_TAG = "tag:yaml.org,2002:merge"


class _UniqueKeyLoader(yaml.SafeLoader):
    def compose_mapping_node(self, anchor: str | None) -> yaml.MappingNode:
        # Checked at compose time, before SafeConstructor.flatten_mapping merges << entries.
        node = super().compose_mapping_node(anchor)
        own = [
            key
            for key, _value in node.value
            if isinstance(key, yaml.ScalarNode) and key.tag != _MERGE_TAG
        ]
        identities = [(key.tag, key.value) for key in own]
        repeated = [
            key
            for index, key in enumerate(own)
            if (key.tag, key.value) in identities[:index]
        ]
        if repeated:
            key = repeated[0]
            line = key.start_mark.line + 1
            raise ComposerError(problem=f"found duplicate key {key.value!r} on line {line}")
        return node


def parse_yaml(text: str) -> object:
    return yaml.load(text, Loader=_UniqueKeyLoader)
