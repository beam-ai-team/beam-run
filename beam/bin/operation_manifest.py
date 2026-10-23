#!/usr/bin/env python3
"""Export the canonical operation contract without a runtime YAML dependency."""
import json
import re
from pathlib import Path

SAFETY = {'read', 'additive-write', 'reversible-write', 'destructive-write', 'external-effect'}
CONFIRMATION = {'none', 'always', 'always-two-turn', 'confirm-proposed-values', 'explicit',
                'explicit-agent-name-and-id', 'explicit-publish-intent', 'explicit-workspace-create-intent',
                'required-if-credentials-or-external-effect', 'required-if-production-side-effect'}
SERIALIZERS = {'value', 'repeated-value', 'boolean', 'json', 'json-file', 'text-file', 'artifact'}


def validate_operations(operations):
    ids = {operation['id'] for operation in operations}
    if not operations or len(ids) != len(operations):
        raise ValueError('Invalid operation registry')
    for operation in operations:
        label = operation['id']
        execution = operation.get('execution')
        if operation.get('status') != 'ready' or not execution or not execution.get('commands'):
            raise ValueError('Incomplete operation: ' + label)
        if operation.get('safety') not in SAFETY or operation.get('confirmation', 'none') not in CONFIRMATION:
            raise ValueError('Invalid operation safety policy: ' + label)
        for action in ('preRead', 'postRead'):
            if action in operation and operation[action] not in ids:
                raise ValueError('Unknown verification operation: ' + label + '/' + action)
        schema = execution['inputSchema']
        properties = schema.get('properties', {})
        required = set(schema.get('required', []))
        if schema.get('type') != 'object' or schema.get('additionalProperties') is not False or not required <= properties.keys():
            raise ValueError('Operation inputs must be closed and valid: ' + label)
        bound = set()
        for command in execution['commands']:
            if not command or not isinstance(command[0].get('literal'), str):
                raise ValueError('Command must start with a fixed executable mapping: ' + label)
            for argument in command:
                if 'literal' in argument:
                    if set(argument) != {'literal'} or not isinstance(argument['literal'], str) or '\0' in argument['literal']:
                        raise ValueError('Invalid literal argument: ' + label)
                    continue
                field = argument.get('field')
                if field not in properties or argument.get('kind') not in SERIALIZERS:
                    raise ValueError('Unbound argument or unsupported serializer: ' + label)
                if set(argument) - {'field', 'kind', 'flag', 'optional'}:
                    raise ValueError('Unknown argument descriptor: ' + label)
                if 'optional' in argument and not isinstance(argument['optional'], bool):
                    raise ValueError('Invalid optional argument: ' + label)
                flag = argument.get('flag')
                if flag is not None and (not isinstance(flag, str) or not flag.startswith('--') or '\0' in flag):
                    raise ValueError('Invalid argument flag: ' + label)
                if argument['kind'] == 'boolean' and (not flag or properties[field].get('type') != 'boolean'):
                    raise ValueError('Boolean serializer needs a boolean field and flag: ' + label)
                if argument['kind'] == 'repeated-value' and (not flag or properties[field].get('type') != 'array'):
                    raise ValueError('Repeated serializer needs an array field and flag: ' + label)
                bound.add(field)
        if bound != properties.keys():
            raise ValueError('Input lacks an executable mapping: ' + label)


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
    validate_operations(operations)
    for operation in operations:
        operation.setdefault('confirmation', 'none')
        operation['workspaceRequired'] = operation.get('workspaceRequired') != 'false'
    return {'schemaVersion': 1, 'version': (root / 'VERSION').read_text().strip(), 'operations': operations}


if __name__ == '__main__':
    print(json.dumps(manifest(), separators=(',', ':')))
