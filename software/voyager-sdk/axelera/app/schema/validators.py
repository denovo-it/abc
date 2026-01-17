# Copyright Axelera AI, 2025

import re

import strictyaml as sy


class AllowDashValidator(sy.ScalarValidator):
    def validate_scalar(self, chunk):
        return re.sub(r'[-_]', '', chunk.contents)


class CaseInsensitiveEnumValidator(sy.ScalarValidator):
    def __init__(self, values):
        self.values = values
        self.values_lower = [v.lower() for v in values]

    def validate_scalar(self, chunk):
        if chunk.contents.lower() in self.values_lower:
            # Return the original case version
            index = self.values_lower.index(chunk.contents.lower())
            return self.values[index]
        raise sy.exceptions.YAMLValidationError(
            f"when expecting one of {self.values}", f"found '{chunk.contents}'", chunk
        )


class IntEnumValidator(sy.ScalarValidator):
    def __init__(self, values):
        self.values = [int(v) for v in values]

    def validate_scalar(self, chunk):
        try:
            if int(chunk.contents) in self.values:
                return int(chunk.contents)
        finally:
            raise sy.exceptions.YAMLValidationError(
                f"when expecting one of {self.values}", f"found '{chunk.contents}'", chunk
            )


class OperatorMapValidator(sy.Map):
    """
    Custom validator for operator maps that provides more helpful error messages
    when an undeclared operator is used in the pipeline.
    """

    def validate(self, chunk):
        try:
            return super().validate(chunk)
        except sy.exceptions.YAMLValidationError as e:
            if match := re.search(r"unexpected key not in schema '([^']+)'", e.problem):
                problem = f"{e.problem}, did you forget to declare '{match.group(1)}' in the operators section?"
                raise sy.exceptions.YAMLValidationError(e.context, problem, chunk)
            raise


class LabelTypeValidator(sy.ScalarValidator):
    def __init__(self):
        from ax_datasets.objdataadapter import SupportedLabelType

        self.label_type_enum = SupportedLabelType

    def validate_scalar(self, chunk):
        try:
            # Use the improved from_string method
            enum_value = self.label_type_enum.from_string(chunk.contents)
            return enum_value.name
        except ValueError:
            # Generate error with all valid format options
            valid_formats = set()
            # Include keys from mapping
            for key in self._get_mapping_keys():
                valid_formats.add(key)
            # Include enum names
            for member in self.label_type_enum:
                valid_formats.add(member.name)

            raise sy.exceptions.YAMLValidationError(
                f"when expecting one of {sorted(list(valid_formats))}",
                f"found '{chunk.contents}'",
                chunk,
            )

    def _get_mapping_keys(self):
        """Get keys from the mapping dictionary in from_string method"""
        import inspect

        source = inspect.getsource(self.label_type_enum.from_string)
        keys = []
        if 'mapping = {' in source:
            mapping_str = source.split('mapping = {')[1].split('}')[0]
            for line in mapping_str.strip().split('\n'):
                if ':' in line:
                    key = line.split(':')[0].strip().strip("'\"")
                    if key:
                        keys.append(key)
        return keys


class NullValidator(sy.Validator):
    def validate(self, chunk):
        if chunk.contents == "null":
            return None
        else:
            raise sy.exceptions.YAMLValidationError(
                "when expecting null", f"found {chunk.contents}", chunk
            )
