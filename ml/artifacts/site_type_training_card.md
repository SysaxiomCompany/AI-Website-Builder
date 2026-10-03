# Site-type classifier (tool report)

Produced by ML-Training-App/text_pipeline.train_text_model; the metrics below are on the team-authored test split (templated prompts, optimistic).

## Training setup

- Feature mode: `tfidf`
- Rows (train / val / test): 840 / 180 / 180
- Seed: 42
- Trained at (UTC): 2026-10-03T18:07:44Z
- TF-IDF parameters: `{"word_ngram_range": [1, 2], "char_ngram_range": [2, 5], "min_df": 1, "sublinear_tf": true, "lowercase": true, "max_features": null}`
- Classifier chosen on the validation set: `logreg(C=10.0,balanced)` (val_macro_f1 = 0.9834); candidates tried: logreg(C=10.0,balanced), logreg(C=30.0,balanced), logreg(C=3.0,balanced), logreg(C=1.0,balanced); refit on train+val: False

## Test-set results (classification)

- Test rows: 180
- Accuracy: 0.9889
- Macro F1: 0.9889
- Weighted F1: 0.9889

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| portfolio | 1.000 | 1.000 | 1.000 | 30 |
| restaurant | 1.000 | 0.967 | 0.983 | 30 |
| small_business | 1.000 | 0.967 | 0.983 | 30 |
| education | 1.000 | 1.000 | 1.000 | 30 |
| blog | 0.968 | 1.000 | 0.984 | 30 |
| nonprofit | 0.968 | 1.000 | 0.984 | 30 |

Weakest classes by F1: restaurant (0.983), small_business (0.983), blog (0.984).

Confusion matrix (rows = true, columns = predicted, in the label order above):

```
  30    0    0    0    0    0
   0   29    0    0    1    0
   0    0   29    0    0    1
   0    0    0   30    0    0
   0    0    0    0   30    0
   0    0    0    0    0   30
```

## Reproducibility

Library versions: sklearn 1.9.1, numpy 2.4.6, pandas 3.0.6, joblib 1.6.0, scipy 1.17.1.

## Limitations

- Team-authored templated prompts; accuracy is not general accuracy.
