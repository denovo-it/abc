# Copyright Axelera AI, 2025

import numpy as np
import torch
import tqdm

from axelera import types
from axelera.app import logging_utils

LOG = logging_utils.getLogger(__name__)


def get_evaluate_cy():
    try:
        from .reid_rank_cy import evaluate_cy

        return evaluate_cy
    except ImportError:
        LOG.trace("Cython reid_rank_cy not available. Compiling on the fly.")
        import logging

        import numpy as np
        import pyximport

        # https://github.com/cython/cython/issues/5380
        # pyximport affects logging level; we should get rid of it after
        # having a proper cython build system
        original_level = logging.root.level
        try:
            pyximport.install(setup_args={"include_dirs": np.get_include()})
            from .reid_rank_cy import evaluate_cy

            return evaluate_cy
        finally:
            logging.root.setLevel(original_level)


evaluate_cy = get_evaluate_cy()


def organize_results(map, rank1):
    metric_names = ['mAP', 'Rank1']
    aggregator_dict = {'mAP': ['average'], 'Rank1': ['average']}

    eval_result = types.EvalResult(
        metric_names=metric_names,
        aggregators=aggregator_dict,
        key_metric='mAP',
        key_aggregator='average',
    )

    eval_result.set_metric_result('mAP', map, 'average', is_percentage=True)
    eval_result.set_metric_result('Rank1', rank1, 'average', is_percentage=True)

    return eval_result


class ReIdEvaluator(types.Evaluator):
    """Evaluator for person re-identification tasks.

    This evaluator computes standard ReID metrics including mAP and Rank-1 accuracy
    by comparing features from query and gallery image sets.
    """

    def __init__(self, **kwargs):
        """Initialize the ReID evaluator."""
        self.data = {}
        self.sample_counts = {"query": 0, "gallery": 0}
        self.unique_pids = {"query": set(), "gallery": set()}
        self.unique_camids = {"query": set(), "gallery": set()}
        self.warned_about_balance = False
        self.log_frequency = 200  # Log progress every N samples
        self.dump_embeddings_to = kwargs.get('dump_embeddings_to', '')

    def process_meta(self, meta) -> None:
        """Process embeddings and metadata from inference.

        Args:
            meta: A metadata object containing ReID features and ground truth information.
        """
        # Extract embedding from inference results
        embedding = np.array(meta.to_evaluation().data)
        split_name = meta.access_ground_truth().split_name

        # Initialize data structure for this split if not exists
        if split_name not in self.data:
            self.data[split_name] = {
                "features": [],
                "pids": [],
                "camids": [],
            }

        # Extract and normalize person_id and camera_id
        person_id = meta.access_ground_truth().person_id
        camera_id = meta.access_ground_truth().camera_id

        if not isinstance(person_id, (list, np.ndarray)):
            person_id = [person_id]
        if not isinstance(camera_id, (list, np.ndarray)):
            camera_id = [camera_id]

        # Update tracking information for query and gallery splits
        if split_name in ["query", "gallery"]:
            self.sample_counts[split_name] += 1
            for pid in person_id:
                self.unique_pids[split_name].add(pid)
            for cid in camera_id:
                self.unique_camids[split_name].add(cid)

        # Store feature and metadata
        self.data[split_name]["features"].append(torch.tensor(embedding))
        self.data[split_name]["pids"].extend(person_id)
        self.data[split_name]["camids"].extend(camera_id)

        # Log progress and check dataset balance periodically
        self._log_progress_and_check_balance()

    def collect_metrics(self):
        """Compute ReID evaluation metrics and optionally dump embeddings.

        Returns:
            An EvalResult object containing mAP and Rank-1 metrics.
        """
        if not self._validate_evaluation_data():
            return organize_results(0.0, 0.0)

        qf, q_pids, q_camids = self._prepare_query_data()
        gf, g_pids, g_camids = self._prepare_gallery_data()

        if self.dump_embeddings_to:
            self._dump_embeddings(qf, q_pids, q_camids, gf, g_pids, g_camids)

        # Compute distance matrix
        LOG.info(
            f"Computing distance matrix for {qf.shape[0]} queries and {gf.shape[0]} gallery items..."
        )
        distmat = self._compute_distance_matrix(qf, gf)

        # Calculate metrics
        LOG.info("Evaluating ReID metrics...")
        try:
            cmc, mAP = evaluate_cy(
                distmat, q_pids, g_pids, q_camids, g_camids, max_rank=1, use_metric_cuhk03=False
            )
            return organize_results(mAP, float(cmc[0]))
        except Exception as e:
            LOG.error(f"Error during ReID evaluation: {str(e)}")
            LOG.error(f"Query PIDs shape: {q_pids.shape}, Gallery PIDs shape: {g_pids.shape}")
            LOG.error(f"Distance matrix shape: {distmat.shape}")
            return organize_results(0.0, 0.0)

    def _log_progress_and_check_balance(self):
        """Log processing progress and check dataset balance."""
        total_samples = sum(self.sample_counts.values())
        if total_samples % self.log_frequency != 0:
            return

        # Check balance after processing enough samples
        if total_samples >= 400 and not self.warned_about_balance:
            query_count = self.sample_counts.get("query", 0)
            gallery_count = self.sample_counts.get("gallery", 0)

            if query_count > 0 and gallery_count > 0:
                ratio = max(query_count, gallery_count) / min(query_count, gallery_count)
                if ratio > 5:
                    LOG.warning(
                        f"Dataset is severely imbalanced: {query_count} query vs {gallery_count} gallery samples (ratio {ratio:.1f})"
                    )
                    self.warned_about_balance = True
            elif query_count > 200 and gallery_count == 0:
                LOG.warning(
                    f"Processing only query samples ({query_count}) with no gallery samples. Evaluation will fail."
                )
                self.warned_about_balance = True
            elif gallery_count > 200 and query_count == 0:
                LOG.warning(
                    f"Processing only gallery samples ({gallery_count}) with no query samples. Evaluation will fail."
                )
                self.warned_about_balance = True

        # Log progress information
        LOG.trace(
            f"Processed {total_samples} samples: {self.sample_counts.get('query', 0)} query, {self.sample_counts.get('gallery', 0)} gallery"
        )

        # Check for common IDs
        common_pids = self.unique_pids.get("query", set()).intersection(
            self.unique_pids.get("gallery", set())
        )
        LOG.trace(
            f"Unique IDs - Query: {len(self.unique_pids.get('query', set()))}, Gallery: {len(self.unique_pids.get('gallery', set()))}"
        )
        LOG.trace(f"Common identities between query and gallery: {len(common_pids)}")

    def _validate_evaluation_data(self):
        """Check if we have valid data for evaluation.

        Returns:
            bool: True if data is valid, False otherwise.
        """
        # Check if both query and gallery splits are available
        if "query" not in self.data or "gallery" not in self.data:
            LOG.warning(
                "Missing required splits for ReID evaluation. Need both 'query' and 'gallery'."
            )
            return False

        # Check if we have any features to evaluate
        if not self.data["query"]["features"] or not self.data["gallery"]["features"]:
            LOG.warning("No features found in either query or gallery sets")
            return False

        # Check if there are any common identities between query and gallery
        query_pids_set = set(self.data["query"]["pids"])
        gallery_pids_set = set(self.data["gallery"]["pids"])
        common_pids = query_pids_set.intersection(gallery_pids_set)

        if not common_pids:
            LOG.warning(
                "No common identities found between query and gallery sets! Evaluation will fail."
            )
            LOG.info(f"Query IDs: {sorted(list(query_pids_set)[:10])}... (showing first 10)")
            LOG.info(f"Gallery IDs: {sorted(list(gallery_pids_set)[:10])}... (showing first 10)")
            return False

        # Log dataset statistics
        LOG.info(f"ReID evaluation dataset statistics:")
        LOG.info(
            f"  Query: {len(self.data['query']['pids'])} images, {len(query_pids_set)} identities"
        )
        LOG.info(
            f"  Gallery: {len(self.data['gallery']['pids'])} images, {len(gallery_pids_set)} identities"
        )
        LOG.info(
            f"  Common identities: {len(common_pids)} (these are the ones that can be matched)"
        )
        return True

    def _prepare_query_data(self):
        """Prepare query data for evaluation.

        Returns:
            tuple: (features, person_ids, camera_ids)
        """
        features = torch.cat(self.data["query"]["features"], 0)
        pids = np.array(self.data["query"]["pids"])
        camids = np.array(self.data["query"]["camids"])
        return features, pids, camids

    def _prepare_gallery_data(self):
        """Prepare gallery data for evaluation.

        Returns:
            tuple: (features, person_ids, camera_ids)
        """
        features = torch.cat(self.data["gallery"]["features"], 0)
        pids = np.array(self.data["gallery"]["pids"])
        camids = np.array(self.data["gallery"]["camids"])
        return features, pids, camids

    def _compute_distance_matrix(self, query_features, gallery_features):
        """Compute distance matrix between query and gallery features.

        Computes distance matrix in chunks to avoid memory issues.

        Args:
            query_features: Tensor of query features
            gallery_features: Tensor of gallery features

        Returns:
            numpy.ndarray: Distance matrix of shape (num_query, num_gallery)
        """
        chunk_size = 1000
        num_query = query_features.shape[0]
        num_gallery = gallery_features.shape[0]
        distmat = np.zeros((num_query, num_gallery), dtype=np.float32)

        for start in tqdm.tqdm(range(0, num_query, chunk_size), desc="Processing query chunks"):
            end = min(start + chunk_size, num_query)
            distmat[start:end] = torch.cdist(
                query_features[start:end], gallery_features, p=2
            ).numpy()

        return distmat

    def _dump_embeddings(self, qf, q_pids, q_camids, gf, g_pids, g_camids):
        """Dump query and gallery embeddings to file.

        Args:
            qf (Tensor): Query features.
            q_pids (ndarray): Query person IDs.
            q_camids (ndarray): Query camera IDs.
            gf (Tensor): Gallery features.
            g_pids (ndarray): Gallery person IDs.
            g_camids (ndarray): Gallery camera IDs.
        """
        import os

        directory = os.path.dirname(self.dump_embeddings_to)
        if directory:  # Only create directory if there is one specified
            os.makedirs(directory, exist_ok=True)

        # Combine query and gallery features
        all_features = torch.cat([qf, gf], dim=0)
        all_pids = np.concatenate([q_pids, g_pids])
        all_camids = np.concatenate([q_camids, g_camids])

        LOG.info(f"Dumping embeddings to {self.dump_embeddings_to}...")
        np.savez_compressed(
            self.dump_embeddings_to,
            features=all_features.cpu().numpy(),
            pids=all_pids,
            camids=all_camids,
        )
        LOG.info("Embedding dump complete.")
