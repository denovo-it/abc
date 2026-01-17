# Copyright Axelera AI, 2025
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest
import yaml

from axelera.app import logging_utils
from axelera.app.format_converters.ultralytics import (
    parse_ultralytics_data_yaml,
    process_ultralytics_data_yaml,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_ultralytics_yaml_content():
    """Sample Ultralytics data YAML content."""
    return {
        'path': '../datasets/my_dataset',
        'train': 'images/train',
        'val': 'images/val',
        'test': 'images/test',
        'nc': 2,
        'names': ['guns', 'knife'],
    }


@pytest.fixture
def sample_ultralytics_yaml_dict_names():
    """Sample Ultralytics data YAML with dictionary-format names."""
    return {
        'path': '../datasets/my_dataset',
        'train': 'train/images',
        'val': 'val/images',
        'nc': 3,
        'names': {0: 'person', 1: 'car', 2: 'bicycle'},
    }


@pytest.fixture
def sample_ultralytics_yaml_file_based():
    """Sample Ultralytics data YAML with file-based image lists."""
    return {
        'path': '/absolute/path/to/dataset',
        'train': 'train_images.txt',
        'val': 'val_images.txt',
        'nc': 1,
        'names': ['license_plate'],
    }


@pytest.fixture
def mock_dataset_structure(temp_dir):
    """Create a mock dataset structure."""
    # Create directory structure
    (temp_dir / 'train' / 'images').mkdir(parents=True)
    (temp_dir / 'train' / 'labels').mkdir(parents=True)
    (temp_dir / 'val' / 'images').mkdir(parents=True)
    (temp_dir / 'val' / 'labels').mkdir(parents=True)

    # Create sample images
    for split in ['train', 'val']:
        for i in range(3):
            img_path = temp_dir / split / 'images' / f'image_{i}.jpg'
            img_path.write_text("fake_image_content")

            label_path = temp_dir / split / 'labels' / f'image_{i}.txt'
            label_path.write_text(f"0 0.5 0.5 0.3 0.3\n")

    return temp_dir


class TestParseUltralyticsDataYaml:
    """Test the parse_ultralytics_data_yaml function."""

    def test_parse_basic_format(self, temp_dir, sample_ultralytics_yaml_content):
        """Test parsing basic Ultralytics YAML format."""
        yaml_file = temp_dir / 'data.yaml'
        with open(yaml_file, 'w') as f:
            yaml.dump(sample_ultralytics_yaml_content, f)

        result = parse_ultralytics_data_yaml(yaml_file, 'test_dataset', temp_dir)

        # The function should return internal format with labels_path (always present)
        assert 'labels_path' in result
        # cal_data and val_data only created if directories/files exist and contain images

        # Check labels file content
        if 'labels_path' in result:
            labels_path = Path(result['labels_path'])
            assert labels_path.exists()
            labels_content = labels_path.read_text().strip().split('\n')
            assert labels_content == ['guns', 'knife']
            # Cleanup
            labels_path.unlink(missing_ok=True)

        # Cleanup any created temp files
        for key in ['cal_data', 'val_data']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)

    def test_parse_dict_names_format(self, temp_dir):
        """Test parsing Ultralytics YAML with dictionary-format names."""
        yaml_content = {
            'path': '../datasets/my_dataset',
            'train': 'train/images',
            'val': 'val/images',
            'nc': 3,
            'names': {0: 'person', 1: 'car', 2: 'bicycle'},
        }
        yaml_file = temp_dir / 'data.yaml'
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        result = parse_ultralytics_data_yaml(yaml_file, 'test_dataset', temp_dir)

        # Check that labels file was created with correct content
        assert 'labels_path' in result
        labels_path = Path(result['labels_path'])
        assert labels_path.exists()
        labels_content = labels_path.read_text().strip().split('\n')
        assert labels_content == ['person', 'car', 'bicycle']

        # Cleanup temp files
        labels_path.unlink(missing_ok=True)
        for key in ['cal_data', 'val_data']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)

    def test_parse_file_not_found(self, temp_dir):
        """Test error handling when YAML file doesn't exist."""
        yaml_file = temp_dir / 'nonexistent.yaml'

        with pytest.raises(ValueError, match="Ultralytics data YAML file not found"):
            parse_ultralytics_data_yaml(yaml_file, 'test_dataset', temp_dir)

    def test_parse_invalid_yaml(self, temp_dir):
        """Test error handling for invalid YAML syntax."""
        yaml_file = temp_dir / 'invalid.yaml'
        yaml_file.write_text("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            parse_ultralytics_data_yaml(yaml_file, 'test_dataset', temp_dir)

    def test_parse_missing_required_fields(self, temp_dir):
        """Test parsing with missing fields - should still work, just no train/val data."""
        yaml_file = temp_dir / 'incomplete.yaml'
        incomplete_content = {'nc': 2}  # Missing names, train, val
        with open(yaml_file, 'w') as f:
            yaml.dump(incomplete_content, f)

        # This should work - names defaults to empty list
        result = parse_ultralytics_data_yaml(yaml_file, 'test_dataset', temp_dir)
        assert 'labels_path' in result

        # Cleanup
        for key in ['labels_path', 'cal_data', 'val_data']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)


class TestUltralyticsYamlParsing:
    """Test end-to-end parsing of Ultralytics YAML configurations."""

    def test_complete_yaml_parsing(self, temp_dir, mock_dataset_structure):
        """Test parsing a complete Ultralytics YAML with real dataset structure."""
        # Create data.yaml file in the mock dataset
        data_yaml = mock_dataset_structure / 'data.yaml'
        yaml_content = {
            'train': 'train/images',
            'val': 'val/images',
            'nc': 2,
            'names': ['gun', 'knife'],
        }
        with open(data_yaml, 'w') as f:
            yaml.dump(yaml_content, f)

        # Parse the YAML
        result = parse_ultralytics_data_yaml(
            data_yaml, 'test_dataset', mock_dataset_structure.parent
        )

        # Check that all expected fields are present
        assert 'labels_path' in result
        assert 'cal_data' in result
        assert 'val_data' in result

        # Check that label file was created and contains correct content
        labels_path = Path(result['labels_path'])
        assert labels_path.exists()
        labels_content = labels_path.read_text().strip().split('\n')
        assert labels_content == ['gun', 'knife']

        # Check that temp files were created for cal_data and val_data
        cal_data_path = Path(result['cal_data'])
        val_data_path = Path(result['val_data'])
        assert cal_data_path.exists()
        assert val_data_path.exists()

        # Cleanup temp files
        labels_path.unlink(missing_ok=True)
        cal_data_path.unlink(missing_ok=True)
        val_data_path.unlink(missing_ok=True)


class TestProcessUltralyticsDataYaml:
    """Test the process_ultralytics_data_yaml function."""

    def test_process_successful(self, temp_dir, mock_dataset_structure):
        """Test successful processing of Ultralytics data YAML."""
        # Create data.yaml file
        data_yaml = mock_dataset_structure / 'data.yaml'
        yaml_content = {
            'train': 'train/images',
            'val': 'val/images',
            'nc': 2,
            'names': ['gun', 'knife'],
        }
        with open(data_yaml, 'w') as f:
            yaml.dump(yaml_content, f)

        # Create dataset config
        dataset = {'ultralytics_data_yaml': 'data.yaml', 'data_dir_name': 'test_dataset'}

        # Set up data_root to point to our mock structure
        data_root = temp_dir / 'data_root'
        data_root.mkdir(exist_ok=True)
        test_dataset_path = data_root / 'test_dataset'
        if test_dataset_path.exists():
            if test_dataset_path.is_symlink():
                test_dataset_path.unlink()
            else:
                import shutil

                shutil.rmtree(test_dataset_path)
        test_dataset_path.symlink_to(mock_dataset_structure)

        process_ultralytics_data_yaml(dataset, 'test_dataset', data_root)

        # Check that the processing worked
        assert 'cal_data' in dataset
        assert 'val_data' in dataset
        assert 'labels_path' in dataset
        assert 'ultralytics_data_yaml' in dataset  # Should be kept for validation

        # Check that temporary files were created
        assert Path(dataset['cal_data']).exists()
        assert Path(dataset['val_data']).exists()
        assert Path(dataset['labels_path']).exists()

        # Check labels file content
        labels_content = Path(dataset['labels_path']).read_text().strip().split('\n')
        assert labels_content == ['gun', 'knife']

    def test_process_missing_ultralytics_yaml(self, temp_dir):
        """Test behavior when ultralytics_data_yaml is not in dataset config."""
        dataset = {'some_other_key': 'value'}
        original_dataset = dataset.copy()

        process_ultralytics_data_yaml(dataset, 'test_dataset', temp_dir)

        # Should be unchanged
        assert dataset == original_dataset

    def test_process_incompatible_keys_error(self, temp_dir):
        """Test error when incompatible keys are present."""
        dataset = {
            'ultralytics_data_yaml': 'data.yaml',
            'cal_data': 'train.txt',  # Incompatible!
            'data_dir_name': 'test_dataset',
        }

        with pytest.raises(ValueError, match="ultralytics_data_yaml cannot be used together"):
            process_ultralytics_data_yaml(dataset, 'test_dataset', temp_dir)

    def test_process_file_not_found_error(self, temp_dir):
        """Test error when ultralytics YAML file doesn't exist."""
        dataset = {'ultralytics_data_yaml': 'nonexistent.yaml', 'data_dir_name': 'test_dataset'}

        # Create the dataset directory
        (temp_dir / 'test_dataset').mkdir()

        with pytest.raises(ValueError, match="Ultralytics data YAML file not found"):
            process_ultralytics_data_yaml(dataset, 'test_dataset', temp_dir)

    @patch('axelera.app.format_converters.ultralytics.parse_ultralytics_data_yaml')
    def test_process_handles_parsing_error(self, mock_parse, temp_dir):
        """Test error handling when YAML parsing fails."""
        mock_parse.side_effect = ValueError("Invalid YAML content")

        # Create a fake data.yaml file
        dataset_dir = temp_dir / 'test_dataset'
        dataset_dir.mkdir()
        (dataset_dir / 'data.yaml').write_text("fake content")

        dataset = {'ultralytics_data_yaml': 'data.yaml', 'data_dir_name': 'test_dataset'}

        with pytest.raises(ValueError, match="Failed to process Ultralytics data YAML"):
            process_ultralytics_data_yaml(dataset, 'test_dataset', temp_dir)


class TestIntegrationWithNetworkParsing:
    """Test integration with the network parsing functionality."""

    @patch('axelera.app.format_converters.process_ultralytics_data_yaml')
    def test_network_parsing_calls_ultralytics_processor(self, mock_process):
        """Test that network parsing calls the Ultralytics processor when needed."""
        from axelera.app.network import parse_and_validate_datasets

        datasets = {
            'test_dataset': {
                'ultralytics_data_yaml': 'data.yaml',
                'data_dir_name': 'test_dataset',
                'class': 'ObjDataAdapter',
                'class_path': '/path/to/adapter.py',
            }
        }

        with patch('axelera.app.data_utils.download_custom_dataset'):
            parse_and_validate_datasets(datasets, Path('/tmp'), False)

        # Verify that the Ultralytics processor was called
        mock_process.assert_called_once_with(
            datasets['test_dataset'], 'test_dataset', Path('/tmp')
        )

    def test_validation_allows_ultralytics_dataset(self):
        """Test that validation allows datasets with ultralytics_data_yaml."""
        from ax_datasets.objdataadapter import ObjDataAdapter
        from axelera import types

        dataset_config = {'ultralytics_data_yaml': 'data.yaml', 'label_type': 'YOLOv8'}

        model_info = types.ModelInfo(
            name='test_model',
            task_category='ObjectDetection',
            input_tensor_shape=[1, 3, 640, 640],
            input_color_format='RGB',
            input_tensor_layout='NCHW',
        )

        # This should not raise an error
        adapter = ObjDataAdapter(dataset_config, model_info)
        assert adapter.label_type.name == 'YOLOv8'


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""

    def test_malformed_names_dict(self, temp_dir):
        """Test handling of malformed names dictionary."""
        yaml_file = temp_dir / 'data.yaml'
        malformed_content = {
            'train': 'train/images',
            'val': 'val/images',
            'nc': 2,
            'names': {1: 'second_class'},  # Missing class 0!
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(malformed_content, f)

        # The implementation is more robust - it sorts dict keys, so missing 0 will cause KeyError during list access
        # But this happens during the list comprehension, not in our code
        result = parse_ultralytics_data_yaml(yaml_file, 'test_dataset', temp_dir)
        # The result will have names = ['second_class'] (only the value for key 1)

        labels_path = Path(result['labels_path'])
        labels_content = labels_path.read_text().strip().split('\n')
        assert labels_content == ['second_class']  # Only the class with index 1

        # Cleanup
        for key in ['labels_path', 'cal_data', 'val_data']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)

    def test_mismatched_nc_and_names(self, temp_dir):
        """Test handling when nc doesn't match names length."""
        yaml_file = temp_dir / 'data.yaml'
        mismatched_content = {
            'train': 'train/images',
            'val': 'val/images',
            'nc': 5,  # Says 5 classes
            'names': ['class1', 'class2'],  # But only 2 names!
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(mismatched_content, f)

        # This should still work - nc field is not validated, only names matter
        result = parse_ultralytics_data_yaml(yaml_file, 'test_dataset', temp_dir)
        assert 'labels_path' in result

        # Cleanup
        for key in ['labels_path', 'cal_data', 'val_data']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)

    def test_empty_names_list(self, temp_dir):
        """Test handling of empty names list."""
        yaml_file = temp_dir / 'data.yaml'
        empty_names_content = {'train': 'train/images', 'val': 'val/images', 'nc': 0, 'names': []}
        with open(yaml_file, 'w') as f:
            yaml.dump(empty_names_content, f)

        result = parse_ultralytics_data_yaml(yaml_file, 'test_dataset', temp_dir)

        # Should still create labels file, even if empty
        assert 'labels_path' in result
        labels_path = Path(result['labels_path'])
        assert labels_path.exists()
        labels_content = labels_path.read_text().strip()
        assert labels_content == ""  # Should be empty

        # Cleanup
        for key in ['labels_path', 'cal_data', 'val_data']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)


class TestUltralyticsSplitPrioritization:
    """Test the improved split prioritization logic."""

    def test_prioritization_with_all_splits(self, temp_dir):
        """Test Case 1: train + val + test -> train=cal_data, test=val_data."""
        # Create all three splits
        for split in ['train', 'val', 'test']:
            split_dir = temp_dir / split / 'images'
            split_dir.mkdir(parents=True)
            for i in range(2):
                img_file = split_dir / f'{split}_{i}.jpg'
                img_file.write_text(f"fake_{split}_image_{i}")

        yaml_file = temp_dir / 'data.yaml'
        yaml_content = {
            'train': 'train/images',
            'val': 'val/images',
            'test': 'test/images',
            'nc': 1,
            'names': ['object'],
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        result = parse_ultralytics_data_yaml(yaml_file, 'test_all_splits', temp_dir)

        # Should use train as cal_data and test as val_data (not val)
        assert 'cal_data' in result
        assert 'val_data' in result

        # Verify the content comes from the right splits
        with open(result['cal_data'], 'r') as f:
            cal_images = f.read()
        with open(result['val_data'], 'r') as f:
            val_images = f.read()

        assert 'train_0.jpg' in cal_images
        assert 'train_1.jpg' in cal_images
        assert 'test_0.jpg' in val_images
        assert 'test_1.jpg' in val_images
        # val split should not be used
        assert 'val_0.jpg' not in cal_images
        assert 'val_0.jpg' not in val_images

        # Cleanup
        for key in ['cal_data', 'val_data', 'labels_path']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)

    def test_prioritization_train_val_only(self, temp_dir):
        """Test Case 2: train + val -> train=cal_data, val=val_data."""
        # Create train and val splits only
        for split in ['train', 'val']:
            split_dir = temp_dir / split / 'images'
            split_dir.mkdir(parents=True)
            for i in range(2):
                img_file = split_dir / f'{split}_{i}.jpg'
                img_file.write_text(f"fake_{split}_image_{i}")

        yaml_file = temp_dir / 'data.yaml'
        yaml_content = {
            'train': 'train/images',
            'val': 'val/images',
            'nc': 1,
            'names': ['object'],
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        result = parse_ultralytics_data_yaml(yaml_file, 'test_train_val', temp_dir)

        # Should use train as cal_data and val as val_data
        assert 'cal_data' in result
        assert 'val_data' in result

        # Verify the content comes from the right splits
        with open(result['cal_data'], 'r') as f:
            cal_images = f.read()
        with open(result['val_data'], 'r') as f:
            val_images = f.read()

        assert 'train_0.jpg' in cal_images
        assert 'val_0.jpg' in val_images

        # Cleanup
        for key in ['cal_data', 'val_data', 'labels_path']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)

    def test_prioritization_val_test_only(self, temp_dir):
        """Test Case 3: val + test (no train) -> val=cal_data, test=val_data."""
        # Create val and test splits only
        for split in ['val', 'test']:
            split_dir = temp_dir / split / 'images'
            split_dir.mkdir(parents=True)
            for i in range(2):
                img_file = split_dir / f'{split}_{i}.jpg'
                img_file.write_text(f"fake_{split}_image_{i}")

        yaml_file = temp_dir / 'data.yaml'
        yaml_content = {
            'val': 'val/images',
            'test': 'test/images',
            'nc': 1,
            'names': ['object'],
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        result = parse_ultralytics_data_yaml(yaml_file, 'test_val_test', temp_dir)

        # Should use val as cal_data and test as val_data
        assert 'cal_data' in result
        assert 'val_data' in result

        # Verify the content comes from the right splits
        with open(result['cal_data'], 'r') as f:
            cal_images = f.read()
        with open(result['val_data'], 'r') as f:
            val_images = f.read()

        assert 'val_0.jpg' in cal_images
        assert 'test_0.jpg' in val_images

        # Cleanup
        for key in ['cal_data', 'val_data', 'labels_path']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)

    def test_prioritization_single_split_train(self, temp_dir):
        """Test Case 4a: only train -> train used for both cal_data and val_data."""
        # Create only train split
        train_dir = temp_dir / 'train' / 'images'
        train_dir.mkdir(parents=True)
        for i in range(2):
            img_file = train_dir / f'train_{i}.jpg'
            img_file.write_text(f"fake_train_image_{i}")

        yaml_file = temp_dir / 'data.yaml'
        yaml_content = {
            'train': 'train/images',
            'nc': 1,
            'names': ['object'],
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        with patch('axelera.app.format_converters.ultralytics.LOG') as mock_log:
            result = parse_ultralytics_data_yaml(yaml_file, 'test_single_train', temp_dir)

            # Should warn about using same data for both
            mock_log.warning.assert_called()
            warning_call = mock_log.warning.call_args[0][0]
            assert 'Only train split available' in warning_call
            assert 'both cal_data and val_data' in warning_call

        # Should use train for both cal_data and val_data
        assert 'cal_data' in result
        assert 'val_data' in result
        assert result['cal_data'] == result['val_data']

        # Cleanup
        for key in ['cal_data', 'val_data', 'labels_path']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)

    def test_prioritization_single_split_val(self, temp_dir):
        """Test Case 4b: only val -> val used for both cal_data and val_data."""
        # Create only val split
        val_dir = temp_dir / 'val' / 'images'
        val_dir.mkdir(parents=True)
        for i in range(2):
            img_file = val_dir / f'val_{i}.jpg'
            img_file.write_text(f"fake_val_image_{i}")

        yaml_file = temp_dir / 'data.yaml'
        yaml_content = {
            'val': 'val/images',
            'nc': 1,
            'names': ['object'],
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        with patch('axelera.app.format_converters.ultralytics.LOG') as mock_log:
            result = parse_ultralytics_data_yaml(yaml_file, 'test_single_val', temp_dir)

            # Should warn about using same data for both
            mock_log.warning.assert_called()
            warning_call = mock_log.warning.call_args[0][0]
            assert 'Only val split available' in warning_call

        # Should use val for both cal_data and val_data
        assert 'cal_data' in result
        assert 'val_data' in result
        assert result['cal_data'] == result['val_data']

        # Cleanup
        for key in ['cal_data', 'val_data', 'labels_path']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)

    def test_prioritization_train_only_with_test(self, temp_dir):
        """Test edge case: train + test (no val) -> train=cal_data, test=val_data."""
        # Create train and test splits only
        for split in ['train', 'test']:
            split_dir = temp_dir / split / 'images'
            split_dir.mkdir(parents=True)
            for i in range(2):
                img_file = split_dir / f'{split}_{i}.jpg'
                img_file.write_text(f"fake_{split}_image_{i}")

        yaml_file = temp_dir / 'data.yaml'
        yaml_content = {
            'train': 'train/images',
            'test': 'test/images',
            'nc': 1,
            'names': ['object'],
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        result = parse_ultralytics_data_yaml(yaml_file, 'test_train_test', temp_dir)

        # Should use train as cal_data and test as val_data
        assert 'cal_data' in result
        assert 'val_data' in result

        # Verify the content comes from the right splits
        with open(result['cal_data'], 'r') as f:
            cal_images = f.read()
        with open(result['val_data'], 'r') as f:
            val_images = f.read()

        assert 'train_0.jpg' in cal_images
        assert 'test_0.jpg' in val_images

        # Cleanup
        for key in ['cal_data', 'val_data', 'labels_path']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)

    def test_logging_messages(self, temp_dir):
        """Test that appropriate logging messages are generated."""
        # Create train and val splits
        for split in ['train', 'val']:
            split_dir = temp_dir / split / 'images'
            split_dir.mkdir(parents=True)
            img_file = split_dir / f'{split}_0.jpg'
            img_file.write_text(f"fake_{split}_image")

        yaml_file = temp_dir / 'data.yaml'
        yaml_content = {
            'train': 'train/images',
            'val': 'val/images',
            'nc': 1,
            'names': ['object'],
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        with patch('axelera.app.format_converters.ultralytics.LOG') as mock_log:
            result = parse_ultralytics_data_yaml(yaml_file, 'test_logging', temp_dir)

            # Should log info about the mapping choice - check all info calls
            mock_log.info.assert_called()
            info_calls = [call[0][0] for call in mock_log.info.call_args_list]
            prioritization_messages = [
                msg
                for msg in info_calls
                if 'Using train split as cal_data and val split as val_data' in msg
            ]
            assert len(prioritization_messages) == 1
            assert 'If you want different mapping' in prioritization_messages[0]

        # Cleanup
        for key in ['cal_data', 'val_data', 'labels_path']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)


class TestUltralyticsPathHandling:
    """Test path field handling in Ultralytics YAML configurations."""

    def test_relative_path_with_relative_splits(self, temp_dir):
        """Test relative path field with train/val/test relative to path."""
        # Create a realistic directory structure: configs/ and datasets/
        configs_dir = temp_dir / 'configs'
        configs_dir.mkdir()
        dataset_root = temp_dir / 'datasets' / 'DOTAv1.5'

        # Create image directories
        for split in ['train', 'val', 'test']:
            split_dir = dataset_root / 'images' / split
            split_dir.mkdir(parents=True)
            # Create sample images
            for i in range(3):
                img_file = split_dir / f'image_{i}.jpg'
                img_file.write_text(f"fake_image_content_{split}_{i}")

        # Create YAML with relative path and relative splits
        yaml_file = configs_dir / 'data.yaml'
        yaml_content = {
            'path': '../datasets/DOTAv1.5',  # relative to YAML location
            'train': 'images/train',  # relative to path
            'val': 'images/val',  # relative to path
            'test': 'images/test',  # relative to path
            'nc': 2,
            'names': ['airplane', 'ship'],
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        # Parse the YAML
        result = parse_ultralytics_data_yaml(yaml_file, 'test_dota', temp_dir)

        # With new prioritization: train=cal_data, test=val_data (val split unused)
        assert 'cal_data' in result
        assert 'val_data' in result
        assert 'labels_path' in result

        # Verify that test split is used for val_data (not val split)
        with open(result['val_data'], 'r') as f:
            val_images = f.read()
        assert 'test' in val_images  # Should contain test images

        # Verify that train split is used for cal_data
        with open(result['cal_data'], 'r') as f:
            cal_images = f.read()
        assert 'train' in cal_images  # Should contain train images

        # Verify labels
        labels_path = Path(result['labels_path'])
        labels_content = labels_path.read_text().strip().split('\n')
        assert labels_content == ['airplane', 'ship']

        # Cleanup temp files
        for key in ['cal_data', 'val_data', 'labels_path']:
            Path(result[key]).unlink(missing_ok=True)

    def test_absolute_path_with_relative_splits(self, temp_dir):
        """Test absolute path field with train/val/test relative to path."""
        # Create dataset structure
        dataset_root = temp_dir / 'datasets' / 'DOTAv1.5'

        # Create image directories
        for split in ['train', 'val', 'test']:
            split_dir = dataset_root / 'images' / split
            split_dir.mkdir(parents=True)
            # Create sample images
            for i in range(2):
                img_file = split_dir / f'image_{i}.jpg'
                img_file.write_text(f"fake_image_content_{split}_{i}")

        # Create YAML with absolute path and relative splits
        yaml_file = temp_dir / 'data.yaml'
        yaml_content = {
            'path': str(dataset_root.absolute()),  # absolute path
            'train': 'images/train',  # relative to path
            'val': 'images/val',  # relative to path
            'test': 'images/test',  # relative to path
            'nc': 3,
            'names': ['airplane', 'ship', 'helicopter'],
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        # Parse the YAML
        result = parse_ultralytics_data_yaml(yaml_file, 'test_dota_abs', temp_dir)

        # With new prioritization: train=cal_data, test=val_data (val split unused)
        assert 'cal_data' in result
        assert 'val_data' in result
        assert 'labels_path' in result

        # Verify that test split is used for val_data (not val split)
        with open(result['val_data'], 'r') as f:
            val_images = f.read()
        assert 'test' in val_images  # Should contain test images

        # Verify that train split is used for cal_data
        with open(result['cal_data'], 'r') as f:
            cal_images = f.read()
        assert 'train' in cal_images  # Should contain train images

        # Verify labels
        labels_path = Path(result['labels_path'])
        labels_content = labels_path.read_text().strip().split('\n')
        assert labels_content == ['airplane', 'ship', 'helicopter']

        # Cleanup temp files
        for key in ['cal_data', 'val_data', 'labels_path']:
            Path(result[key]).unlink(missing_ok=True)

    def test_no_path_field_uses_yaml_parent(self, temp_dir):
        """Test that when no path field is provided, YAML parent directory is used."""
        # Create image directories directly under temp_dir
        for split in ['train', 'val']:
            split_dir = temp_dir / 'images' / split
            split_dir.mkdir(parents=True)
            # Create sample images
            for i in range(2):
                img_file = split_dir / f'image_{i}.jpg'
                img_file.write_text(f"fake_image_content_{split}_{i}")

        # Create YAML without path field
        yaml_file = temp_dir / 'data.yaml'
        yaml_content = {
            # No 'path' field
            'train': 'images/train',  # relative to YAML location
            'val': 'images/val',  # relative to YAML location
            'nc': 1,
            'names': ['object'],
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        # Parse the YAML
        result = parse_ultralytics_data_yaml(yaml_file, 'test_no_path', temp_dir)

        # Verify splits were found
        assert 'cal_data' in result
        assert 'val_data' in result
        assert 'labels_path' in result

        # Verify image counts
        for key in ['cal_data', 'val_data']:
            with open(result[key], 'r') as f:
                lines = f.readlines()
            assert len(lines) == 2  # 2 images per split

        # Cleanup temp files
        for key in ['cal_data', 'val_data', 'labels_path']:
            Path(result[key]).unlink(missing_ok=True)

    def test_path_resolution_with_nonexistent_path(self, temp_dir):
        """Test error handling when path field points to non-existent directory."""
        yaml_file = temp_dir / 'data.yaml'
        yaml_content = {
            'path': '../nonexistent/dataset',
            'train': 'images/train',
            'val': 'images/val',
            'nc': 1,
            'names': ['object'],
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        # Parse should succeed but find no images
        result = parse_ultralytics_data_yaml(yaml_file, 'test_nonexistent', temp_dir)

        # Should have labels but no image data
        assert 'labels_path' in result
        assert 'cal_data' not in result  # No train images found
        assert 'val_data' not in result  # No val images found

        # Cleanup
        if 'labels_path' in result:
            Path(result['labels_path']).unlink(missing_ok=True)

    def test_mixed_absolute_relative_paths_in_splits(self, temp_dir):
        """Test handling when some splits are absolute and some relative."""
        # Create dataset structure
        dataset_root = temp_dir / 'datasets' / 'mixed_test'
        train_dir = dataset_root / 'train'
        train_dir.mkdir(parents=True)

        # Create an external val directory
        external_val_dir = temp_dir / 'external_validation'
        external_val_dir.mkdir()

        # Create sample images
        for i in range(2):
            train_img = train_dir / f'train_{i}.jpg'
            train_img.write_text(f"train_image_{i}")

            val_img = external_val_dir / f'val_{i}.jpg'
            val_img.write_text(f"val_image_{i}")

        # Create YAML with mixed path types
        yaml_file = temp_dir / 'data.yaml'
        yaml_content = {
            'path': str(dataset_root.absolute()),
            'train': 'train',  # relative to path
            'val': str(external_val_dir.absolute()),  # absolute path
            'nc': 1,
            'names': ['mixed'],
        }
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)

        # Parse the YAML
        result = parse_ultralytics_data_yaml(yaml_file, 'test_mixed', temp_dir)

        # Verify both splits were found
        assert 'cal_data' in result
        assert 'val_data' in result

        # Verify image counts
        for key in ['cal_data', 'val_data']:
            with open(result[key], 'r') as f:
                lines = f.readlines()
            assert len(lines) == 2  # 2 images per split

        # Cleanup temp files
        for key in ['cal_data', 'val_data', 'labels_path']:
            if key in result:
                Path(result[key]).unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__])
