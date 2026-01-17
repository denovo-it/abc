#!/usr/bin/env python
# Copyright Axelera AI, 2025

from axelera.app import config, display, logging_utils
from axelera.app.stream import create_inference_stream

source = str(config.env.framework / "media/bowl-of-fruit.mp4")

stream = create_inference_stream(
    network="t9-cascaded",
    sources=[source],
    pipe_type='gst',
)


def main(window, stream):
    """Main processing loop for the video stream"""
    for frame_result in stream:
        window.show(frame_result.image, frame_result.meta)

        if 'detections' not in frame_result.meta:
            print("No detections found in this frame")
            continue

        detection_meta = frame_result.meta['detections']
        num_detections = len(detection_meta.boxes)
        print(f"Found {num_detections} detections")

        print("\n--- OPTION 1: Low-level API access (similar to C++ implementation) ---")
        # This method accesses the metadata using the low-level API directly
        # Similar to how the C++ code works with direct access to metadata
        for i in range(num_detections):
            box = detection_meta.boxes[i]
            midpoint_x = (box[0] + box[2]) / 2
            midpoint_y = (box[1] + box[3]) / 2

            master_class_id = detection_meta.class_ids[i]
            master_score = detection_meta.scores[i]

            # Check if this detection has classification results for the 'classifier' task
            if (
                'classifier' in detection_meta.secondary_frame_indices
                and i in detection_meta.secondary_frame_indices['classifier']
            ):
                # Get classification submeta for this detection
                classifier_meta = detection_meta.get_secondary_meta('classifier', i)

                # Use get_result() to access the class_id and score arrays
                class_ids, scores = classifier_meta.get_result(0)
                class_id = class_ids[0]  # Always an array in this implementation
                score = scores[0]  # Always an array in this implementation

                # Note: If softmax is not enabled in the decoder, raw scores will be higher
                threshold = 2.0  # Threshold for raw scores (not softmaxed)

                if score > threshold:
                    print(
                        f"The box with midpoint ({midpoint_x:.0f}, {midpoint_y:.0f}) has "
                        f"classification class ID {class_id} with confidence {score:.2f}"
                    )
                else:
                    print(
                        f"The box with midpoint ({midpoint_x:.0f}, {midpoint_y:.0f}) has "
                        f"low confidence classification ({score:.2f}), class ID {class_id}"
                    )
            else:
                # Show the actual object class from master detection
                print(
                    f"The box with midpoint ({midpoint_x:.0f}, {midpoint_y:.0f}) has "
                    f"no classification - detected as master class ID "
                    f"{master_class_id} with score {master_score:.2f}"
                )

        print("\n--- OPTION 2: Object-oriented API with metadata access ---")
        # This method uses the more object-oriented approach with metadata objects
        for idx, master in enumerate(frame_result.detections):
            # Calculate midpoint from the bounding box
            box = master.box
            midpoint_x = (box[0] + box[2]) / 2
            midpoint_y = (box[1] + box[3]) / 2

            # Check what secondary tasks this detection has
            available_tasks = master.secondary_task_names

            if 'classifier' in available_tasks:
                # Get classification results using metadata access
                classifier_meta = master.get_secondary_meta('classifier')
                class_ids, scores = classifier_meta.get_result(0)
                class_id = class_ids[0]  # Always an array
                score = scores[0]  # Always an array

                threshold = 2.0
                if score > threshold:
                    print(
                        f"Detection {idx} at ({midpoint_x:.0f}, {midpoint_y:.0f}): "
                        f"class_id={class_id}, confidence={score:.2f}"
                    )
                else:
                    print(
                        f"Detection {idx} at ({midpoint_x:.0f}, {midpoint_y:.0f}): "
                        f"LOW CONFIDENCE class_id={class_id}, score={score:.2f}"
                    )
            else:
                # No classification for this detection
                print(
                    f"Detection {idx} at ({midpoint_x:.0f}, {midpoint_y:.0f}): "
                    f"No classification, master_class={master.class_id}"
                )

        print("\n--- OPTION 3: Simplified object access for secondary results ---")
        # This method provides the most concise way to access secondary objects
        for idx, master in enumerate(frame_result.detections):
            # Get all secondary task names for this detection
            tasks = master.secondary_task_names

            if 'classifier' in tasks:
                # Access secondary objects directly - simplest approach
                secondary_objects = master.get_secondary_objects('classifier')

                for secondary in secondary_objects:
                    # In this implementation, class_id and score are always arrays
                    class_id = secondary.class_id[0]
                    score = secondary.score[0]

                    print(
                        f"Detection {idx} has classifier result: class_id={class_id}, score={score:.2f}"
                    )
            else:
                print(f"Detection {idx} has no classifier results")


with display.App(renderer=True, opengl=stream.hardware_caps.opengl) as app:
    wnd = app.create_window("Cascade Pipeline Demo", (900, 600))
    app.start_thread(main, (wnd, stream), name='InferenceThread')
    app.run(interval=1 / 10)
stream.stop()
