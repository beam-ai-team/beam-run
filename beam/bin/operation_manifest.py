#!/usr/bin/env python3
"""Export the canonical operation contract without a runtime YAML dependency."""
import json
import re
from pathlib import Path


def manifest():
    root = Path(__file__).resolve().parents[1]
    operations = []
    current = None
    for line in (root / 'contracts/operations.yaml').read_text().splitlines():
        match = re.fullmatch(r'  ([a-z][a-z0-9.-]+):', line)
        if match:
            current = {'id': match[1]}
            operations.append(current)
            continue
        field = re.match(r'    (execution|safety|confirmation|workspaceRequired|status|preRead|postRead|notes|cli): (.*)', line)
        if field and current is not None:
            key, value = field.groups()
            current[key] = json.loads(value) if key == 'execution' else value.strip('"')
    for operation in operations:
        execution = operation.get('execution')
        if operation.get('status') != 'ready' or not execution or not execution.get('commands'):
            raise ValueError('Incomplete operation: ' + operation['id'])
        schema = execution['inputSchema']
        if schema.get('additionalProperties') is not False:
            raise ValueError('Operation inputs must be closed: ' + operation['id'])
        for command in execution['commands']:
            for argument in command:
                if 'field' in argument and argument['field'] not in schema['properties']:
                    raise ValueError('Unbound argument: ' + operation['id'] + '/' + argument['field'])
        operation.setdefault('confirmation', 'none')
        operation['workspaceRequired'] = operation.get('workspaceRequired') != 'false'
    if not operations or len({operation['id'] for operation in operations}) != len(operations):
        raise ValueError('Invalid operation registry')
    return {'schemaVersion': 1, 'version': (root / 'VERSION').read_text().strip(), 'operations': operations}


if __name__ == '__main__':
    print(json.dumps(manifest(), separators=(',', ':')))
