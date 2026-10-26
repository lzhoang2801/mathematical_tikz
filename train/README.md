# TikZ fine-tuning

Open [Train.ipynb](Train.ipynb) in a Colab/Kaggle GPU runtime with Internet. Use the updated repository checkout for `evaluation/` and the shared compiler worker; the notebook clones the repository when run standalone.

The notebook follows the supplied [Unsloth Qwen3.5 Vision recipe](https://github.com/unslothai/notebooks/blob/main/nb/Qwen3_5_(4B)_Vision.ipynb): install, load HF data, preview, build task messages, train, save, infer, evaluate and upload. It uses `model`, `tokenizer`, `converted_dataset`, `trainer` and `trainer_stats`, and native Unsloth save/push methods.

- Dataset: [`lzhoang2601/mathematical-tikz`](https://huggingface.co/datasets/lzhoang2601/mathematical-tikz), revision `61ec212baa25007bb06304c7dac8df0e96b1967b`; configurations `reconstruct`, `generate`, `edit`.
- Only training splits train the model. Validation loss and diagram metrics are separate. No task resampling or new split assignment is performed.
- Complete conversations must fit `max_length`; image/padding masking remains the native vision collator's behavior.
- After fine-tuning, the explicit inference section exports bounded validation predictions and shows generated TikZ plus a rendered result for each task. Evaluation reuses those exact outputs and their cached observations. The final optional cell reloads a saved/uploaded adapter in a fresh session.
- Diagram evaluation reuses [evaluation.batch](../evaluation/batch.py) and the current PGF observer/scorer. The default is at most five validation predictions per task; exact outputs, duplicate IDs, partial scores and compiler errors are retained.
- Checkpoints, adapter, predictions, scores and previews go under a new `runs/fine-tuning/<UTC timestamp>/`. Upload the adapter with `push_to_hub`; the last cell shows optional `push_to_hub_merged`.

[evaluate.py](evaluate.py) retains only the notebook transport/cache for the pinned shared compiler worker. Historical pilots, notebooks, scripts and results are preserved under `runs/training/legacy-20261026/`; these Git-ignored files must be copied explicitly when transferring the workspace.
