# Copyright Axelera AI, 2025
# Tests for the dependency graph implementation

import contextlib
from unittest.mock import MagicMock, patch

import pytest
import yaml

from axelera import types
from axelera.app.network import parse_network_from_path
from axelera.app.operators import Input, InputFromROI, InputWithImageProcessing
from axelera.app.pipe.graph import DependencyGraph, EdgeType, NetworkType


class TestDependencyGraph:
    def create_mock_task(
        self,
        name,
        is_dl_task=True,
        task_category=types.TaskCategory.ObjectDetection,
        input_type=None,
        input_source=None,
        input_where=None,
        embeddings_task_name=None,
    ):
        """Helper to create mock tasks with specified properties"""
        task = MagicMock()
        task.name = name
        task.is_dl_task = is_dl_task

        # Set up model info
        task.model_info = MagicMock()
        task.model_info.name = f"{name}_model"
        task.model_info.task_category = task_category

        # Set up input based on parameters
        if input_type == "ROI" and input_where:
            task.input = InputFromROI(where=input_where)
        elif input_type == "full":
            task.input = Input()
        elif input_type == "image_processing":
            task.input = InputWithImageProcessing()
        else:
            task.input = Input()

        # For tracker tasks
        if task_category == types.TaskCategory.ObjectTracking:
            task.is_dl_task = False
            cv_process = MagicMock()
            cv_process.bbox_task_name = input_where
            # Add embeddings_task_name if provided
            if embeddings_task_name:
                cv_process.embeddings_task_name = embeddings_task_name
            task.cv_process = [cv_process]

        return task

    def test_simple_tracker_graph(self):
        """Test a simple detector + tracker pipeline"""
        # Create mock tasks similar to yolov5m-v7-coco-tracker.yaml
        detector = self.create_mock_task("detections")
        tracker = self.create_mock_task(
            "pedestrian_tracker",
            is_dl_task=False,
            task_category=types.TaskCategory.ObjectTracking,
            input_type="full",
            input_where="detections",
        )

        # Create dependency graph
        graph = DependencyGraph([detector, tracker])

        # Test execution view
        assert "detections" in graph.graph["Input"]
        assert "pedestrian_tracker" in graph.graph["detections"]

        # Test result view (tracker should be directly connected to input)
        assert "pedestrian_tracker" in graph.result_graph["Input"]
        assert "pedestrian_tracker" not in graph.result_graph["detections"]

        # Test get_master with different views
        assert graph.get_master("pedestrian_tracker", EdgeType.EXECUTION) == "detections"
        assert graph.get_master("pedestrian_tracker", EdgeType.RESULT) is None

        # Test network type
        assert graph.network_type == NetworkType.CASCADE_NETWORK

    def test_complex_cascade_graph(self):
        """Test a complex cascade with multiple branches"""
        # Create mock tasks similar to yolov5m-v7-coco-tracker_reid.yaml
        detector = self.create_mock_task("detections")
        reid = self.create_mock_task(
            "reid",
            task_category=types.TaskCategory.ObjectDetection,
            input_type="ROI",
            input_where="detections",
        )
        tracker = self.create_mock_task(
            "tracking",
            is_dl_task=False,
            task_category=types.TaskCategory.ObjectTracking,
            input_type="full",
            input_where="detections",
        )
        person_attr = self.create_mock_task(
            "person_attributes", input_type="ROI", input_where="tracking"
        )
        vehicle_attr = self.create_mock_task(
            "vehicle_attributes", input_type="ROI", input_where="tracking"
        )

        # Create dependency graph
        tasks = [detector, reid, tracker, person_attr, vehicle_attr]
        graph = DependencyGraph(tasks)

        # Test execution view connections
        assert "detections" in graph.graph["Input"]
        assert "reid" in graph.graph["detections"]
        assert "tracking" in graph.graph["detections"]
        assert "person_attributes" in graph.graph["tracking"]
        assert "vehicle_attributes" in graph.graph["tracking"]

        # Test result view (tracker should be directly connected to input)
        assert "tracking" in graph.result_graph["Input"]
        assert "tracking" not in graph.result_graph["detections"]
        assert "person_attributes" in graph.result_graph["tracking"]
        assert "vehicle_attributes" in graph.result_graph["tracking"]

        # Test get_master with different views
        assert graph.get_master("tracking", EdgeType.EXECUTION) == "detections"
        assert graph.get_master("tracking", EdgeType.RESULT) is None
        assert graph.get_master("person_attributes", EdgeType.EXECUTION) == "tracking"
        assert graph.get_master("person_attributes", EdgeType.RESULT) == "tracking"

        # Test network type
        assert graph.network_type == NetworkType.COMPLEX_NETWORK

    def test_fruit_detection_cascade(self):
        """Test a complex cascade with parallel branches"""
        # Create mock tasks similar to ces2025-ln.yaml
        master_detections = self.create_mock_task("master_detections")
        segmentations = self.create_mock_task(
            "segmentations",
            task_category=types.TaskCategory.ObjectDetection,
            input_type="ROI",
            input_where="master_detections",
        )
        object_detections = self.create_mock_task("object_detections")

        # Create dependency graph
        tasks = [master_detections, segmentations, object_detections]
        graph = DependencyGraph(tasks)

        # Test execution view connections
        assert "master_detections" in graph.graph["Input"]
        assert "object_detections" in graph.graph["Input"]
        assert "segmentations" in graph.graph["master_detections"]

        # Test result view (should be the same as execution view in this case)
        assert "master_detections" in graph.result_graph["Input"]
        assert "object_detections" in graph.result_graph["Input"]
        assert "segmentations" in graph.result_graph["master_detections"]

        # Test get_master
        assert graph.get_master("segmentations") == "master_detections"
        assert graph.get_master("master_detections") is None
        assert graph.get_master("object_detections") is None

        # Test network type
        assert graph.network_type == NetworkType.COMPLEX_NETWORK

    def test_single_model_network(self):
        """Test a single model network"""
        detector = self.create_mock_task("detections")
        graph = DependencyGraph([detector])

        assert graph.network_type == NetworkType.SINGLE_MODEL
        assert "detections" in graph.graph["Input"]

        # Test get_root_and_leaf_tasks
        root, leaf = graph.get_root_and_leaf_tasks()
        assert root == "detections"
        assert leaf == "detections"

    def test_cascade_network(self):
        """Test a simple cascade network"""
        detector = self.create_mock_task("detections")
        classifier = self.create_mock_task(
            "classifications", input_type="ROI", input_where="detections"
        )

        graph = DependencyGraph([detector, classifier])

        assert graph.network_type == NetworkType.CASCADE_NETWORK

        # Test get_root_and_leaf_tasks
        root, leaf = graph.get_root_and_leaf_tasks()
        assert root == "detections"
        assert leaf == "classifications"

    def test_task_validation(self):
        """Test task validation"""
        detector = self.create_mock_task("detections")
        graph = DependencyGraph([detector])

        # Test valid task
        graph.get_task("detections")

        # Test invalid task
        with pytest.raises(ValueError, match="Task invalid_task not found in the pipeline"):
            graph.get_task("invalid_task")

        # Test model name instead of task name
        # Make sure the model name is in the model_names list
        graph.model_names = ["detections_model"]
        with pytest.raises(ValueError, match="Task detections_model is a model, not a task"):
            graph.get_task("detections_model")

    def test_clear_cache(self):
        """Test cache clearing"""
        detector = self.create_mock_task("detections")
        classifier = self.create_mock_task(
            "classifications", input_type="ROI", input_where="detections"
        )

        graph = DependencyGraph([detector, classifier])

        # Call get_master to populate cache
        master = graph.get_master("classifications")
        assert master == "detections"

        # Clear cache and verify it still works
        graph.clear_cache()
        master = graph.get_master("classifications")
        assert master == "detections"

    def test_tracker_with_reid_cascade(self):
        """Test a tracker cascade with detection and re-identification"""
        # Create mock tasks similar to the tracker with reid example
        detector = self.create_mock_task("detections")
        reid = self.create_mock_task(
            "reid",
            task_category=types.TaskCategory.ObjectDetection,
            input_type="ROI",
            input_where="detections",
        )
        tracker = self.create_mock_task(
            "pedestrian_and_vehicle_tracker",
            is_dl_task=False,
            task_category=types.TaskCategory.ObjectTracking,
            input_type="full",
            input_where="detections",
            embeddings_task_name="reid",
        )

        # Create dependency graph
        graph = DependencyGraph([detector, reid, tracker])

        # Test execution view connections
        assert "detections" in graph.graph["Input"]
        assert "reid" in graph.graph["detections"]
        assert "pedestrian_and_vehicle_tracker" in graph.graph["detections"]
        assert "pedestrian_and_vehicle_tracker" in graph.graph["reid"]

        # Test result view (tracker should be directly connected to input)
        assert "pedestrian_and_vehicle_tracker" in graph.result_graph["Input"]
        assert "pedestrian_and_vehicle_tracker" not in graph.result_graph["detections"]
        assert "pedestrian_and_vehicle_tracker" not in graph.result_graph["reid"]

        # Test get_master with different views
        assert (
            graph.get_master("pedestrian_and_vehicle_tracker", EdgeType.EXECUTION) == "detections"
        )
        assert graph.get_master("pedestrian_and_vehicle_tracker", EdgeType.RESULT) is None
        assert graph.get_master("reid", EdgeType.EXECUTION) == "detections"

        # Test network type - should be a cascade now with our improved detection
        assert graph.network_type == NetworkType.CASCADE_NETWORK

        # Test get_root_and_leaf_tasks
        root, leaf = graph.get_root_and_leaf_tasks()
        assert root == "detections"
        assert leaf == "pedestrian_and_vehicle_tracker"


class TestDependencyGraphIntegration:
    def parse_network_yaml(self, yaml_str, template_yaml=""):
        """Parse a YAML string into an AxNetwork using the actual parser"""
        # Create a mock file system with our YAML strings
        files = {'test.yaml': yaml_str, 'template.yaml': template_yaml}

        # Mock the file system operations
        def mock_isfile(path):
            return path.name in files

        def mock_readtext(path, *args):
            try:
                return files[path.name]
            except KeyError:
                raise FileNotFoundError(path) from None

        # Use the actual parser with our mocked file system
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch('pathlib.Path.is_file', new=mock_isfile))
            stack.enter_context(patch('pathlib.Path.read_text', new=mock_readtext))
            return parse_network_from_path('test.yaml')

    def test_simple_tracker_graph(self):
        """Test a simple detector + tracker pipeline"""
        yaml_str = """
name: simple-tracker
description: Simple detector + tracker pipeline
pipeline:
  - detections:
      model_name: yolov5m
      template_path: template.yaml
  - pedestrian_tracker:
      model_name: oc_sort
      input:
        source: full
        color_format: BGR
      cv_process:
        - tracker:
            algorithm: oc-sort
            bbox_task_name: detections
            label_filter:
              - person
models:
  yolov5m:
    task_category: ObjectDetection
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 640, 640]
    input_color_format: RGB
  oc_sort:
    model_type: CLASSICAL_CV
    task_category: ObjectTracking
"""

        template_yaml = """
preprocess:
  - resize:
      width: 640
      height: 640
"""

        # Parse the network
        network = self.parse_network_yaml(yaml_str, template_yaml)

        # Create the dependency graph
        graph = DependencyGraph(network.tasks)

        # Test execution view
        assert "detections" in graph.graph["Input"]
        assert "pedestrian_tracker" in graph.graph["detections"]

        # Test result view (tracker should be directly connected to input)
        assert "pedestrian_tracker" in graph.result_graph["Input"]
        assert "pedestrian_tracker" not in graph.result_graph["detections"]

        # Test get_master with different views
        assert graph.get_master("pedestrian_tracker", EdgeType.EXECUTION) == "detections"
        assert graph.get_master("pedestrian_tracker", EdgeType.RESULT) is None

        # Test network type
        assert graph.network_type == NetworkType.CASCADE_NETWORK

    def test_complex_cascade_graph(self):
        """Test a complex cascade with multiple branches"""
        yaml_str = """
name: complex-cascade
description: Complex cascade with multiple branches
pipeline:
  - detections:
      model_name: yolov5m
      template_path: template.yaml
  - reid:
      model_name: sbs_s50
      input:
        source: roi
        where: detections
  - tracking:
      model_name: tracker
      input:
        source: full
        color_format: BGR
      cv_process:
        - tracker:
            algorithm: oc-sort
            bbox_task_name: detections
            embeddings_task_name: reid
  - person_attributes:
      model_name: ResNet50
      input:
        type: image
        source: roi
        where: tracking
  - vehicle_attributes:
      model_name: ResNet-Vehicle
      input:
        type: image
        source: roi
        where: tracking
models:
  yolov5m:
    task_category: ObjectDetection
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 640, 640]
    input_color_format: RGB
  sbs_s50:
    task_category: ObjectDetection
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 112, 112]
    input_color_format: RGB
  tracker:
    model_type: CLASSICAL_CV
    task_category: ObjectTracking
  ResNet50:
    task_category: Classification
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 224, 224]
    input_color_format: RGB
  ResNet-Vehicle:
    task_category: Classification
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 224, 224]
    input_color_format: RGB
"""

        template_yaml = """
preprocess:
  - resize:
      width: 640
      height: 640
"""

        # Parse the network
        network = self.parse_network_yaml(yaml_str, template_yaml)

        # Create the dependency graph
        graph = DependencyGraph(network.tasks)

        # Test execution view connections
        assert "detections" in graph.graph["Input"]
        assert "reid" in graph.graph["detections"]
        assert "tracking" in graph.graph["detections"]
        assert "person_attributes" in graph.graph["tracking"]
        assert "vehicle_attributes" in graph.graph["tracking"]

        # Test result view (tracker should be directly connected to input)
        assert "tracking" in graph.result_graph["Input"]
        assert "tracking" not in graph.result_graph["detections"]
        assert "person_attributes" in graph.result_graph["tracking"]
        assert "vehicle_attributes" in graph.result_graph["tracking"]

        # Test get_master with different views
        assert graph.get_master("tracking", EdgeType.EXECUTION) == "detections"
        assert graph.get_master("tracking", EdgeType.RESULT) is None
        assert graph.get_master("person_attributes", EdgeType.EXECUTION) == "tracking"
        assert graph.get_master("person_attributes", EdgeType.RESULT) == "tracking"

        # Test network type
        assert graph.network_type == NetworkType.COMPLEX_NETWORK

    def test_fruit_detection_cascade(self):
        """Test a complex cascade with parallel branches"""
        yaml_str = """
name: fruit-detection
description: Complex cascade with parallel branches
pipeline:
  - master_detections:
      model_name: yolov8lpose
      input:
        type: image
      preprocess:
        - letterbox:
            width: 640
            height: 640
  - segmentations:
      model_name: yolov8nseg
      template_path: template.yaml
      input:
        type: image
        source: roi
        where: master_detections
  - object_detections:
      model_name: yolov8n
      input:
        type: image
models:
  yolov8lpose:
    task_category: KeypointDetection
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 640, 640]
    input_color_format: RGB
  yolov8nseg:
    task_category: InstanceSegmentation
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 640, 640]
    input_color_format: RGB
  yolov8n:
    task_category: ObjectDetection
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 640, 640]
    input_color_format: RGB
"""

        template_yaml = """
preprocess:
  - resize:
      width: 640
      height: 640
"""

        # Parse the network
        network = self.parse_network_yaml(yaml_str, template_yaml)

        # Create the dependency graph
        graph = DependencyGraph(network.tasks)

        # Test execution view connections
        assert "master_detections" in graph.graph["Input"]
        assert "object_detections" in graph.graph["Input"]
        assert "segmentations" in graph.graph["master_detections"]

        # Test result view (should be the same as execution view in this case)
        assert "master_detections" in graph.result_graph["Input"]
        assert "object_detections" in graph.result_graph["Input"]
        assert "segmentations" in graph.result_graph["master_detections"]

        # Test get_master
        assert graph.get_master("segmentations") == "master_detections"
        assert graph.get_master("master_detections") is None
        assert graph.get_master("object_detections") is None

        # Test network type - this is a complex network because it has both parallel and cascade elements
        assert graph.network_type == NetworkType.COMPLEX_NETWORK

    def test_single_model_network(self):
        """Test a single model network"""
        yaml_str = """
name: single-model
description: Single model network
pipeline:
  - detections:
      model_name: yolov5m
      template_path: template.yaml
models:
  yolov5m:
    task_category: ObjectDetection
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 640, 640]
    input_color_format: RGB
"""

        template_yaml = """
preprocess:
  - resize:
      width: 640
      height: 640
"""

        # Parse the network
        network = self.parse_network_yaml(yaml_str, template_yaml)

        # Create the dependency graph
        graph = DependencyGraph(network.tasks)

        assert graph.network_type == NetworkType.SINGLE_MODEL
        assert "detections" in graph.graph["Input"]

        # Test get_root_and_leaf_tasks
        root, leaf = graph.get_root_and_leaf_tasks()
        assert root == "detections"
        assert leaf == "detections"

    def test_cascade_network(self):
        """Test a simple cascade network"""
        yaml_str = """
name: cascade-network
description: Simple cascade network
pipeline:
  - detections:
      model_name: yolov5m
      template_path: template.yaml
  - classifications:
      model_name: resnet50
      input:
        source: roi
        where: detections
models:
  yolov5m:
    task_category: ObjectDetection
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 640, 640]
    input_color_format: RGB
  resnet50:
    task_category: Classification
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 224, 224]
    input_color_format: RGB
"""

        template_yaml = """
preprocess:
  - resize:
      width: 640
      height: 640
"""

        # Parse the network
        network = self.parse_network_yaml(yaml_str, template_yaml)

        # Create the dependency graph
        graph = DependencyGraph(network.tasks)

        assert graph.network_type == NetworkType.CASCADE_NETWORK

        # Test get_root_and_leaf_tasks
        root, leaf = graph.get_root_and_leaf_tasks()
        assert root == "detections"
        assert leaf == "classifications"

    def test_parallel_network(self):
        """Test a parallel network"""
        yaml_str = """
name: parallel-network
description: Parallel network
pipeline:
  - face_detection:
      model_name: face_detection_model
      input:
        type: image
  - person_detection:
      model_name: person_detection_model
      input:
        type: image
  - vehicle_detection:
      model_name: vehicle_detection_model
      input:
        type: image
models:
  face_detection_model:
    task_category: ObjectDetection
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 640, 640]
    input_color_format: RGB
  person_detection_model:
    task_category: ObjectDetection
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 640, 640]
    input_color_format: RGB
  vehicle_detection_model:
    task_category: ObjectDetection
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 640, 640]
    input_color_format: RGB
"""

        # Parse the network
        network = self.parse_network_yaml(yaml_str)

        # Create the dependency graph
        graph = DependencyGraph(network.tasks)

        # All tasks should be connected to Input
        assert "face_detection" in graph.graph["Input"]
        assert "person_detection" in graph.graph["Input"]
        assert "vehicle_detection" in graph.graph["Input"]

        # No connections between tasks
        assert graph.graph["face_detection"] == []
        assert graph.graph["person_detection"] == []
        assert graph.graph["vehicle_detection"] == []

        # Test network type
        assert graph.network_type == NetworkType.PARALLEL_NETWORK

        lines = []
        graph.print_graph(lines.append)
        assert '''
--- EXECUTION VIEW ---
Input
│ └─face_detection
│ └─person_detection
  └─vehicle_detection''' == "\n".join(
            lines
        )

    def test_tracker_reid_cascade_integration(self):
        """Test a tracker cascade with detection and re-identification from YAML"""
        yaml_str = """
name: reid-tracker-cascade
description: Detection + ReID + Tracker cascade network
pipeline:
  - detections:
      model_name: yolox-pedestrian-onnx
      preprocess:
        - resize:
            width: 640
            height: 640
        - torch-totensor:
      postprocess:
  - reid:
      model_name: osnet-x1-0-market1501-onnx
      input:
        type: image
        source: roi
        where: detections
      preprocess:
        - resize:
            width: 128
            height: 256
        - torch-totensor:
        - normalize:
            mean: [0.485, 0.456, 0.406]
            std: [0.229, 0.224, 0.225]
      postprocess:
        - decodeembeddings:
  - pedestrian_and_vehicle_tracker:
      model_name: oc_sort
      input:
        source: full
        color_format: RGB
      cv_process:
        - tracker:
            algorithm: oc-sort
            bbox_task_name: detections
            embeddings_task_name: reid
            algo_params:
              det_thresh: 0.6
              min_hits: 3
              iou_threshold: 0.3
              max_id: 0
models:
  yolox-pedestrian-onnx:
    task_category: ObjectDetection
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 640, 640]
    input_color_format: RGB
  osnet-x1-0-market1501-onnx:
    task_category: ReIdentification
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 3, 256, 128]
    input_color_format: RGB
  oc_sort:
    model_type: CLASSICAL_CV
    task_category: ObjectTracking
"""

        template_yaml = """
preprocess:
  - letterbox:
      width: 640
      height: 640
"""

        # Parse the network
        network = self.parse_network_yaml(yaml_str, template_yaml)

        # Create the dependency graph
        graph = DependencyGraph(network.tasks)

        # Test execution view connections
        assert "detections" in graph.graph["Input"]
        assert "reid" in graph.graph["detections"]
        assert "pedestrian_and_vehicle_tracker" in graph.graph["detections"]
        assert "pedestrian_and_vehicle_tracker" in graph.graph["reid"]

        # Test result view (tracker should be directly connected to input)
        assert "pedestrian_and_vehicle_tracker" in graph.result_graph["Input"]
        assert "pedestrian_and_vehicle_tracker" not in graph.result_graph["detections"]
        assert "pedestrian_and_vehicle_tracker" not in graph.result_graph["reid"]

        # Test get_master with different views
        assert (
            graph.get_master("pedestrian_and_vehicle_tracker", EdgeType.EXECUTION) == "detections"
        )
        assert graph.get_master("pedestrian_and_vehicle_tracker", EdgeType.RESULT) is None
        assert graph.get_master("reid", EdgeType.EXECUTION) == "detections"

        # Test network type - should be a cascade now with our improved detection
        assert graph.network_type == NetworkType.CASCADE_NETWORK

        # Test get_root_and_leaf_tasks
        root, leaf = graph.get_root_and_leaf_tasks()
        assert root == "detections"
        assert leaf == "pedestrian_and_vehicle_tracker"
