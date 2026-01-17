![](/docs/images/Ax_Page_Banner_2500x168_01.png)
# Additional models

Voyager SDK supports additional models which are, however, not included in our Model Zoo.

## Image Classification

The following classification models can be compiled and their accuracy has been verified. While they don't have dedicated YAML configurations in our model zoo yet, you can easily use them by adapting the existing [mobilenetv4_small-imagenet.yaml](/ax_models/zoo/timm/mobilenetv4_small-imagenet.yaml) template - simply update the timm_model_args.name field to your desired model and adjust the preprocessing configuration as needed.

| Model Name                            | Accuracy Drop (vs. FP32 model) |
| :------------------------------------ | :----------------------------- |
| dla34.in1k                            | 0.59                           |
| dla60.in1k                            | 0.55                           |
| dla60_res2net.in1k                    | 0.15                           |
| dla102.in1k                           | 0.03                           |
| dla169.in1k                           | 0.27                           |
| efficientnet_es.ra_in1k               | 0.02                           |
| efficientnet_es_pruned.in1k           | 0.13                           |
| efficientnet_lite0.ra_in1k            | 0.22                           |
| dla46_c.in1k                          | 1.54                           |
| fbnetc_100.rmsp_in1k                  | 0.24                           |
| gernet_m.idstcv_in1k                  | 0.05                           |
| gernet_s.idstcv_in1k                  | 0.18                           |
| mnasnet_100.rmsp_in1k                 | 0.28                           |
| mobilenetv2_050.lamb_in1k             | 0.92                           |
| mobilenetv2_120d.ra_in1k              | 0.44                           |
| mobilenetv2_140.ra_in1k               | 0.89                           |
| res2net50_14w_8s.in1k                 | 0.17                           |
| res2net50_26w_4s.in1k                 | 0.17                           |
| res2net50_26w_6s.in1k                 | 0.06                           |
| res2net50_48w_2s.in1k                 | 0.09                           |
| res2net50d.in1k                       | 0.00                           |
| res2net101_26w_4s.in1k                | 0.19                           |
| res2net101d.in1k                      | 0.08                           |
| resnet10t.c3_in1k                     | 1.61                           |
| resnet14t.c3_in1k                     | 0.85                           |
| resnet50c.gluon_in1k                  | 0.03                           |
| resnet50s.gluon_in1k                  | 0.19                           |
| resnet101c.gluon_in1k                 | 0.08                           |
| resnet101d.gluon_in1k                 | 0.1                            |
| resnet101s.gluon_in1k                 | 0.18                           |
| resnet152d.gluon_in1k                 | 0.15                           |
| selecsls42b.in1k                      | 0.25                           |
| selecsls60.in1k                       | 0.05                           |
| selecsls60b.in1k                      | 0.2                            |
| spnasnet_100.rmsp_in1k                | 0.25                           |
| tf_efficientnet_es.in1k               | 0.26                           |
| tf_efficientnet_lite0.in1k            | 0.33                           |
| tf_mobilenetv3_large_minimal_100.in1k | 1.68                           |
| wide_resnet101_2.tv2_in1k             | 0.26                           |
