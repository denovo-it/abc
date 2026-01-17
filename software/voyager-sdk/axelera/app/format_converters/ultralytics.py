# Copyright Axelera AI, 2025
# Ultralytics format converter for integrating Ultralytics data YAML format with Axelera

from pathlib import Path
import tempfile
from typing import Dict, Optional

import yaml

from axelera.app import logging_utils

LOG = logging_utils.getLogger(__name__)


def process_ultralytics_data_yaml(
    dataset: dict, dataset_name: str, data_root: Optional[Path]
) -> None:
    """
    Process ultralytics_data_yaml parameter and convert to internal format.

    Args:
        dataset: Dataset configuration dictionary (modified in place)
        dataset_name: Name of the dataset for error reporting
        data_root: Root directory for dataset files
    """
    if 'ultralytics_data_yaml' not in dataset:
        return

    LOG.debug(f"Processing Ultralytics data YAML for dataset {dataset_name}")

    # Validate that ultralytics_data_yaml is not combined with incompatible options
    incompatible_keys = ['cal_data', 'val_data', 'labels_path', 'labels']
    for key in incompatible_keys:
        if key in dataset:
            raise ValueError(
                f"ultralytics_data_yaml cannot be used together with {key} for dataset {dataset_name}"
            )

    ultralytics_yaml_path = Path(dataset['ultralytics_data_yaml'])

    # Make path absolute if relative
    if not ultralytics_yaml_path.is_absolute():
        if data_root is not None:
            if 'data_dir_name' in dataset:
                ultralytics_yaml_path = (
                    data_root / dataset['data_dir_name'] / ultralytics_yaml_path
                )
            else:
                ultralytics_yaml_path = data_root / ultralytics_yaml_path
        else:
            # Make it relative to the current working directory
            ultralytics_yaml_path = ultralytics_yaml_path.resolve()

    try:
        # Parse the Ultralytics YAML and get the converted config
        ultralytics_config = parse_ultralytics_data_yaml(
            ultralytics_yaml_path, dataset_name, data_root
        )

        # Merge the parsed config into the dataset config
        dataset.update(ultralytics_config)

        # DON'T remove the ultralytics_data_yaml key - keep it for validation
        # del dataset['ultralytics_data_yaml']

        LOG.info(f"Successfully processed Ultralytics data YAML for dataset {dataset_name}")

    except Exception as e:
        raise ValueError(
            f"Failed to process Ultralytics data YAML for dataset {dataset_name}: {e}"
        ) from e


def parse_ultralytics_data_yaml(
    ultralytics_yaml_path: Path, dataset_name: str, data_root: Optional[Path]
) -> Dict:
    """
    Parse Ultralytics-format data YAML and convert it to internal format.

    Args:
        ultralytics_yaml_path: Path to the Ultralytics data.yaml file
        dataset_name: Name of the dataset for error reporting
        data_root: Root directory for dataset files

    Returns:
        dict: Dataset configuration in internal format
    """
    if not ultralytics_yaml_path.is_file():
        raise ValueError(f"Ultralytics data YAML file not found: {ultralytics_yaml_path}")

    LOG.debug(f"Parsing Ultralytics data YAML: {ultralytics_yaml_path}")

    # Load the Ultralytics YAML
    with open(ultralytics_yaml_path, 'r') as f:
        ultralytics_data = yaml.safe_load(f)

    if not isinstance(ultralytics_data, dict):
        raise ValueError(f"Invalid Ultralytics data YAML format in {ultralytics_yaml_path}")

    # Extract the dataset root path
    ultralytics_path = ultralytics_data.get('path', '')
    if not ultralytics_path:
        # If no path specified, assume it's relative to the YAML file location
        ultralytics_root = ultralytics_yaml_path.parent
    else:
        # Convert to absolute path
        if Path(ultralytics_path).is_absolute():
            ultralytics_root = Path(ultralytics_path)
        else:
            ultralytics_root = ultralytics_yaml_path.parent / ultralytics_path

    ultralytics_root = ultralytics_root.resolve()

    # Extract class names
    names = ultralytics_data.get('names', [])
    if isinstance(names, dict):
        # Convert {0: 'class1', 1: 'class2'} to ['class1', 'class2']
        names = [
            names[i] for i in sorted(int(k) if isinstance(k, str) else k for k in names.keys())
        ]
    elif not isinstance(names, list):
        raise ValueError(f"'names' in {ultralytics_yaml_path} must be either a list or dictionary")

    # Create a temporary labels file
    temp_labels_file = tempfile.NamedTemporaryFile(
        mode='w+', prefix=f'ax_ultralytics_labels_{dataset_name}_', suffix='.txt', delete=False
    )

    try:
        for name in names:
            temp_labels_file.write(f"{name}\n")
        temp_labels_file.close()
        labels_path = Path(temp_labels_file.name)
        LOG.debug(f"Created temporary labels file at {labels_path} for dataset {dataset_name}")
    except Exception as e:
        temp_labels_file_path = Path(temp_labels_file.name)
        temp_labels_file_path.unlink(missing_ok=True)
        raise ValueError(f"Failed to create labels file for dataset {dataset_name}: {e}")

    # Helper function to create image list files
    def create_image_list_file(split_info, split_name):
        """Create a text file listing image paths for a split."""
        if not split_info:
            return None

        # Handle different formats: directory path, file path, or list of paths
        if isinstance(split_info, str):
            split_paths = [split_info]
        elif isinstance(split_info, list):
            split_paths = split_info
        else:
            raise ValueError(
                f"Invalid {split_name} format in {ultralytics_yaml_path}: {split_info}"
            )

        temp_file = tempfile.NamedTemporaryFile(
            mode='w+',
            prefix=f'ax_ultralytics_{split_name}_{dataset_name}_',
            suffix='.txt',
            delete=False,
        )
        temp_file_path = Path(temp_file.name)

        try:
            image_count = 0
            for split_path in split_paths:
                # Convert to absolute path with intelligent path resolution
                if Path(split_path).is_absolute():
                    full_path = Path(split_path)
                else:
                    # Try multiple path resolution strategies
                    resolved_path = None

                    # Strategy 1: Relative to ultralytics_root (standard)
                    candidate = ultralytics_root / split_path
                    if candidate.exists():
                        resolved_path = candidate
                        LOG.debug(
                            f"Resolved {split_name} path relative to ultralytics_root: {candidate}"
                        )

                    # Strategy 2: Handle ../ paths by removing the parent reference
                    # This handles cases like "../train/images" when the actual structure is "train/images"
                    elif split_path.startswith('../'):
                        # Remove only one ../ prefix (not all of them like lstrip does)
                        clean_path = split_path.removeprefix('../')
                        candidate = ultralytics_root / clean_path
                        if candidate.exists():
                            resolved_path = candidate
                            LOG.debug(
                                f"Resolved {split_name} path by removing ../ prefix: {candidate}"
                            )
                        else:
                            # Strategy 2b: Try alternative naming conventions
                            # For example, ../valid/images might actually be ../val/images or just val/images
                            if 'valid' in clean_path:
                                alt_clean_path = clean_path.replace('valid', 'val')
                                alt_candidate = ultralytics_root / alt_clean_path
                                if alt_candidate.exists():
                                    resolved_path = alt_candidate
                                    LOG.debug(
                                        f"Resolved {split_name} path by replacing 'valid' with 'val': {alt_candidate}"
                                    )

                    # Strategy 3: If data_root is different from ultralytics_root, try relative to data_root
                    if not resolved_path and data_root and data_root != ultralytics_root:
                        candidate = data_root / split_path
                        if candidate.exists():
                            resolved_path = candidate
                            LOG.debug(
                                f"Resolved {split_name} path relative to data_root: {candidate}"
                            )

                    # Strategy 4: Try the clean path relative to data_root
                    if not resolved_path and data_root and split_path.startswith('../'):
                        # Remove only one ../ prefix (not all of them like lstrip does)
                        clean_path = split_path.removeprefix('../')
                        candidate = data_root / clean_path
                        if candidate.exists():
                            resolved_path = candidate
                            LOG.debug(
                                f"Resolved {split_name} path by removing ../ and using data_root: {candidate}"
                            )
                        else:
                            # Strategy 4b: Try alternative naming conventions with data_root
                            if 'valid' in clean_path:
                                alt_clean_path = clean_path.replace('valid', 'val')
                                alt_candidate = data_root / alt_clean_path
                                if alt_candidate.exists():
                                    resolved_path = alt_candidate
                                    LOG.debug(
                                        f"Resolved {split_name} path by replacing 'valid' with 'val' and using data_root: {alt_candidate}"
                                    )

                    # Strategy 5: If no directory path worked, check for a split file in the YAML directory
                    # This handles cases where val: ../valid/images doesn't exist but val.txt does
                    if not resolved_path:
                        yaml_dir = ultralytics_yaml_path.parent
                        # Try [split_name].txt first (e.g., val.txt for 'val' split)
                        split_file_candidate = yaml_dir / f"{split_name}.txt"
                        if split_file_candidate.exists():
                            resolved_path = split_file_candidate
                            LOG.debug(
                                f"Resolved {split_name} path using split file in YAML directory: {split_file_candidate}"
                            )
                        else:
                            # Try alternative naming (e.g., valid.txt for 'val' split)
                            if split_name == 'val' and not resolved_path:
                                alt_split_file = yaml_dir / "valid.txt"
                                if alt_split_file.exists():
                                    resolved_path = alt_split_file
                                    LOG.debug(
                                        f"Resolved {split_name} path using alternative split file: {alt_split_file}"
                                    )

                    full_path = resolved_path if resolved_path else (ultralytics_root / split_path)

                if full_path.is_file():
                    file_suffix = full_path.suffix.lower()

                    # Check if it's a COCO JSON or PascalVOC XML annotation file
                    if file_suffix in ['.json', '.xml']:
                        # For annotation files (JSON/XML), write the path to the file itself
                        # The dataset loader will handle parsing the annotations
                        temp_file.write(f"{full_path.absolute()}\n")
                        image_count += 1
                        format_type = 'COCO JSON' if file_suffix == '.json' else 'PascalVOC XML'
                        LOG.debug(f"Detected {format_type} file for {split_name}: {full_path}")
                    else:
                        # It's a text file containing image paths (one per line)
                        with open(full_path, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    # Make sure the path is absolute
                                    img_path = Path(line)
                                    if not img_path.is_absolute():
                                        img_path = ultralytics_root / line
                                    temp_file.write(f"{img_path.absolute()}\n")
                                    image_count += 1
                elif full_path.is_dir():
                    # It's a directory containing images
                    img_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}
                    for img_file in full_path.rglob('*'):
                        if img_file.suffix.lower() in img_extensions:
                            temp_file.write(f"{img_file.absolute()}\n")
                            image_count += 1
                else:
                    LOG.warning(f"Path not found for {split_name} split: {full_path}")

            temp_file.close()

            if image_count == 0:
                temp_file_path.unlink(missing_ok=True)
                LOG.warning(f"No images found for {split_name} split")
                return None

            LOG.debug(f"Created {split_name} file with {image_count} images at {temp_file_path}")
            return temp_file_path

        except Exception as e:
            temp_file_path.unlink(missing_ok=True)
            raise ValueError(f"Failed to create {split_name} file for dataset {dataset_name}: {e}")

    # Extract and convert train/val/test splits with improved prioritization
    result_config = {}

    # Create temp files for available splits
    available_splits = {}
    for split_name in ['train', 'val', 'test']:
        if split_name in ultralytics_data:
            split_file = create_image_list_file(ultralytics_data[split_name], split_name)
            if split_file:
                available_splits[split_name] = str(split_file)

    # Apply prioritization logic for cal_data and val_data assignment
    cal_data_assigned = False
    val_data_assigned = False

    # Case 1: If there is test data: test -> val_data, train -> cal_data
    if 'test' in available_splits and 'train' in available_splits:
        result_config['cal_data'] = available_splits['train']
        result_config['val_data'] = available_splits['test']
        cal_data_assigned = val_data_assigned = True
        LOG.info(
            f"Dataset {dataset_name}: Using train split as cal_data and test split as val_data. "
            f"If you want different mapping, set cal_data or val_data explicitly in Axelera YAML."
        )

    # Case 2: If no test data: val -> val_data, train -> cal_data
    elif 'train' in available_splits and 'val' in available_splits:
        result_config['cal_data'] = available_splits['train']
        result_config['val_data'] = available_splits['val']
        cal_data_assigned = val_data_assigned = True
        LOG.info(
            f"Dataset {dataset_name}: Using train split as cal_data and val split as val_data. "
            f"If you want different mapping, set cal_data or val_data explicitly in Axelera YAML."
        )

    # Case 3: If no train data but have val and test: val -> cal_data, test -> val_data
    elif 'val' in available_splits and 'test' in available_splits:
        result_config['cal_data'] = available_splits['val']
        result_config['val_data'] = available_splits['test']
        cal_data_assigned = val_data_assigned = True
        LOG.info(
            f"Dataset {dataset_name}: Using val split as cal_data and test split as val_data. "
            f"If you want different mapping, set cal_data or val_data explicitly in Axelera YAML."
        )

    # Case 4: If there is only one split: use that as both cal_data and val_data (with warning)
    elif len(available_splits) == 1:
        split_name, split_file = next(iter(available_splits.items()))
        result_config['cal_data'] = split_file
        result_config['val_data'] = split_file
        cal_data_assigned = val_data_assigned = True
        LOG.warning(
            f"Dataset {dataset_name}: Only {split_name} split available. Using it for both cal_data and val_data. "
            f"This may not be ideal for validation. Consider providing separate calibration and validation data."
        )

    # Handle remaining cases where only partial splits are available
    if not cal_data_assigned:
        # Prioritize train > val > test for cal_data
        for split_name in ['train', 'val', 'test']:
            if split_name in available_splits:
                result_config['cal_data'] = available_splits[split_name]
                cal_data_assigned = True
                LOG.info(
                    f"Dataset {dataset_name}: Using {split_name} split as cal_data. "
                    f"If you want different mapping, set cal_data explicitly in Axelera YAML."
                )
                break

    if not val_data_assigned:
        # Prioritize test > val > train for val_data
        for split_name in ['test', 'val', 'train']:
            if split_name in available_splits and (
                'cal_data' not in result_config
                or result_config['cal_data'] != available_splits[split_name]
            ):
                result_config['val_data'] = available_splits[split_name]
                val_data_assigned = True
                LOG.info(
                    f"Dataset {dataset_name}: Using {split_name} split as val_data. "
                    f"If you want different mapping, set val_data explicitly in Axelera YAML."
                )
                break

    # If still no val_data and we have cal_data, use the same file (with warning)
    if not val_data_assigned and cal_data_assigned:
        result_config['val_data'] = result_config['cal_data']
        LOG.warning(
            f"Dataset {dataset_name}: Using the same data for both calibration and validation. "
            f"This may not be ideal for validation. Consider providing separate validation data."
        )

    # Set labels path
    result_config['labels_path'] = str(labels_path)

    # Set dataset root
    if data_root is not None:
        # Use the provided data_root, but log the ultralytics path for reference
        result_config['data_dir_path'] = data_root
        LOG.debug(
            f"Using provided data_root {data_root} for dataset {dataset_name}, ultralytics path was {ultralytics_root}"
        )
    else:
        # Use the ultralytics dataset root
        result_config['data_dir_path'] = ultralytics_root

    LOG.info(
        f"Successfully parsed Ultralytics data YAML for dataset {dataset_name} with {len(names)} classes"
    )

    return result_config
