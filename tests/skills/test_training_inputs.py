"""Training inputs, native Unsloth calls and prediction identity; no GPU/model calls."""
import ast
import json
from contextlib import nullcontext
from pathlib import Path
import tempfile
import types
from unittest.mock import Mock, call, patch
import unittest

import numpy as np

NOTEBOOK = Path(__file__).resolve().parents[2] / "train/Train.ipynb"


class TrainingInputsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cells = json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]
        cls.code = {tag: "".join(cell["source"]) for cell in cls.cells if cell["cell_type"] == "code"
                    for tag in cell.get("metadata", {}).get("tags", [])}

    def setUp(self):
        self.namespace = {}
        exec(self.code["tikz-prompts"], self.namespace)

    def sample(self, task, suffix=""):
        return {"id": "repeated-image-id", "image": object(),
                "instruction": "Given geometry " + suffix, "current_tikz": "Exact current " + suffix,
                "target_tikz": "Exact target " + suffix, "source": "offline-source",
                "review": "offline-review", "task": task}

    def data(self):
        return {task: {split: [self.sample(task, split)] for split in ("train", "validation", "test")}
                for task in ("reconstruct", "generate", "edit")}

    def test_task_inputs_and_exact_target_are_separated(self):
        convert = self.namespace["convert_to_conversation"]
        for task in ("reconstruct", "generate", "edit"):
            with self.subTest(task=task):
                sample = self.sample(task)
                messages = convert(sample, task)["messages"]
                self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant"])
                self.assertEqual(messages[-1]["content"], [{"type": "text", "text": sample["target_tikz"]}])
                human = messages[1]["content"]
                if task == "reconstruct":
                    self.assertEqual(human, [{"type": "image", "image": sample["image"]}])
                else:
                    self.assertEqual(human[0], {"type": "text", "text": sample["instruction"]})
                    self.assertEqual(len(human), 2 if task == "edit" else 1)
                visible = "\n".join(part.get("text", "") for m in messages[:-1] for part in m["content"])
                for value in (sample["target_tikz"], sample["source"], sample["review"], sample["id"]):
                    self.assertNotIn(value, visible)
                self.assertEqual(sample["current_tikz"] in visible, task == "edit")

    def test_inference_needs_no_target_or_offline_metadata(self):
        convert = self.namespace["convert_to_conversation"]
        for task in ("reconstruct", "generate", "edit"):
            sample = self.sample(task)
            expected = convert(sample, task)["messages"][:-1]
            sample.pop("target_tikz")
            self.assertEqual(convert(sample, task, include_target=False)["messages"], expected)

    def test_missing_inputs_are_rejected(self):
        convert = self.namespace["convert_to_conversation"]
        for task, field in (("reconstruct", "image"), ("generate", "instruction"),
                            ("edit", "instruction"), ("edit", "current_tikz"), ("edit", "target_tikz")):
            sample = self.sample(task); sample[field] = None
            with self.subTest(task=task, field=field), self.assertRaises(ValueError):
                convert(sample, task)
        with self.assertRaises(ValueError):
            convert(self.sample("generate"), "unknown")

    def test_hf_loader_uses_the_selected_repository_revision_and_three_configs(self):
        dataset_module = types.ModuleType("datasets")
        dataset_module.load_dataset = Mock(side_effect=lambda repo, *, name, revision: self.data()[name])
        with tempfile.TemporaryDirectory() as folder, patch.dict("sys.modules", {"datasets": dataset_module}):
            namespace = {"tasks": ("reconstruct", "generate", "edit"),
                         "dataset_name": "lzhoang2601/mathematical-tikz",
                         "dataset_revision": "frozen-revision", "run_dir": Path(folder), "json": json}
            exec(self.code["tikz-load"], namespace)
            self.assertEqual(dataset_module.load_dataset.call_args_list, [
                (("lzhoang2601/mathematical-tikz",), {"name": task, "revision": "frozen-revision"})
                for task in namespace["tasks"]
            ])
            self.assertEqual(set(namespace["dataset"]), set(namespace["tasks"]))
            self.assertEqual(json.loads((Path(folder) / "dataset.json").read_text())["revision"], "frozen-revision")

    def test_prepare_never_trains_validation_or_test_and_does_not_resample(self):
        data = self.data(); data["edit"]["train"].append(self.sample("edit", "train-second"))
        namespace = {**self.namespace, "tasks": tuple(data), "dataset": data, "display": Mock()}
        exec(self.code["tikz-prepare"], namespace)
        targets = lambda rows: [r["messages"][-1]["content"][0]["text"] for r in rows]
        self.assertEqual(len(namespace["converted_dataset"]), 4)
        self.assertEqual(len(namespace["converted_validation_dataset"]), 3)
        self.assertTrue(all("train" in text for text in targets(namespace["converted_dataset"])))
        self.assertTrue(all("validation" in text for text in targets(namespace["converted_validation_dataset"])))
        self.assertEqual(data["generate"]["test"][0]["target_tikz"], "Exact target test")

    def inference_namespace(self):
        class Inputs(dict):
            def to(self, device):
                return self
        tokenizer = Mock()
        tokenizer.apply_chat_template.return_value = "prompt"
        tokenizer.return_value = Inputs(input_ids=np.array([[1, 2, 3]]))
        tokenizer.batch_decode.return_value = ["```latex\nraw output\n```\n"]
        model = types.SimpleNamespace(device="cuda", generate=Mock(return_value=np.array([[1, 2, 3, 4, 5]])))
        namespace = {**self.namespace, "model": model, "tokenizer": tokenizer,
                     "FastVisionModel": types.SimpleNamespace(for_inference=Mock()),
                     "torch": types.SimpleNamespace(inference_mode=nullcontext),
                     "max_seq_length": 4096, "max_new_tokens": 2048, "json": json, "Path": Path,
                     "dataset_revision": "frozen", "dataset": self.data(),
                     "tasks": ("reconstruct", "generate", "edit")}
        exec(self.code["tikz-inference"], namespace)
        return namespace

    def test_generation_excludes_reference_and_keeps_exact_completion(self):
        namespace = self.inference_namespace()
        sample = self.sample("edit")
        result = namespace["generate_tikz"](sample, "edit")
        self.assertEqual(result, "```latex\nraw output\n```\n")
        messages = namespace["tokenizer"].apply_chat_template.call_args.args[0]
        self.assertEqual([m["role"] for m in messages], ["system", "user"])
        self.assertNotIn(sample["target_tikz"], str(messages))
        self.assertEqual(namespace["model"].generate.call_count, 1)
        np.testing.assert_array_equal(namespace["tokenizer"].batch_decode.call_args.args[0], [[4, 5]])

    def test_generation_budget_failure_cannot_call_model(self):
        namespace = self.inference_namespace(); namespace["max_seq_length"] = 2048
        with self.assertRaisesRegex(ValueError, "budget"):
            namespace["generate_tikz"](self.sample("generate"), "generate")
        namespace["model"].generate.assert_not_called()

    def test_predictions_keep_duplicate_ids_row_indices_and_exact_pairs(self):
        namespace = self.inference_namespace()
        for task in namespace["tasks"]:
            namespace["dataset"][task]["validation"].append(self.sample(task, "second"))
        namespace["generate_tikz"] = Mock(return_value="raw output\n")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "predictions.jsonl"
            namespace["export_predictions"](path, limit=2)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 6)
            self.assertEqual(len({r["id"] for r in rows}), 1)
            self.assertEqual(len({(r["task"], r["split"], r["row_index"]) for r in rows}), 6)
            self.assertTrue(all(r["output_tikz"] == "raw output\n" for r in rows))
            self.assertTrue(all(r["dataset_revision"] == "frozen" for r in rows))
            with self.assertRaises(FileExistsError):
                namespace["export_predictions"](path)

    def test_prediction_failure_preserves_completed_rows(self):
        namespace = self.inference_namespace()
        namespace["generate_tikz"] = Mock(side_effect=["first exact output", RuntimeError("GPU failure")])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "predictions.jsonl"
            with self.assertRaisesRegex(RuntimeError, "GPU failure"):
                namespace["export_predictions"](path)
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["output_tikz"], "first exact output")

    def test_trainer_refuses_oversize_or_truncated_targets_before_training(self):
        for token_count, decoded in ((2049, "Exact target train"), (20, "Exact target"), (20, "Exact target train")):
            with self.subTest(token_count=token_count, decoded=decoded):
                trl = types.ModuleType("trl"); trl.SFTTrainer = Mock(); trl.SFTConfig = Mock()
                unsloth = types.ModuleType("unsloth"); collators = types.ModuleType("unsloth.trainer")
                labels = np.array([[-100, 5]])
                collator = Mock(return_value={"input_ids": np.zeros((1, token_count)), "labels": labels})
                collators.UnslothVisionDataCollator = Mock(return_value=collator)
                tokenizer = Mock(); tokenizer.batch_decode.return_value = [decoded]
                namespace = {"FastVisionModel": types.SimpleNamespace(for_training=Mock()), "model": object(),
                             "tokenizer": tokenizer, "max_length": 2048, "run_dir": Path("runs/fixture"),
                             "converted_dataset": [self.namespace["convert_to_conversation"](self.sample("generate", "train"), "generate")],
                             "converted_validation_dataset": []}
                with patch.dict("sys.modules", {"unsloth": unsloth, "unsloth.trainer": collators, "trl": trl}):
                    if token_count > 2048 or decoded != "Exact target train":
                        with self.assertRaisesRegex(ValueError, "max_length"):
                            exec(self.code["unsloth-trainer"], namespace)
                        trl.SFTTrainer.assert_not_called()
                    else:
                        exec(self.code["unsloth-trainer"], namespace)
                        self.assertIs(trl.SFTTrainer.call_args.kwargs["tokenizer"], tokenizer)
                        self.assertIs(trl.SFTTrainer.call_args.kwargs["data_collator"], collator)
                        self.assertEqual(trl.SFTConfig.call_args.kwargs["max_length"], 2048)
                        np.testing.assert_array_equal(labels, [[-100, 5]])

    def test_native_save_and_upload_methods_receive_model_and_tokenizer(self):
        login = types.ModuleType("huggingface_hub"); login.notebook_login = Mock()
        model, tokenizer = Mock(), Mock()
        namespace = {"model": model, "tokenizer": tokenizer, "run_dir": Path("runs/fixture"),
                     "hf_model_id": "owner/tikz-model"}
        exec(self.code["unsloth-save"], namespace)
        with patch.dict("sys.modules", {"huggingface_hub": login}):
            exec(self.code["unsloth-upload"], namespace)
        model.save_pretrained.assert_called_once_with(str(Path("runs/fixture/qwen_lora")))
        tokenizer.save_pretrained.assert_called_once_with(str(Path("runs/fixture/qwen_lora")))
        model.push_to_hub.assert_called_once_with("owner/tikz-model")
        tokenizer.push_to_hub.assert_called_once_with("owner/tikz-model")
        login.notebook_login.assert_called_once()

    def test_explicit_inference_renders_saved_outputs_and_evaluation_reuses_them(self):
        namespace = self.inference_namespace()
        namespace["generate_tikz"] = Mock(side_effect=lambda sample, task: "raw " + task + " output\n")
        compiler = object()
        namespace.update(local_compiler=lambda: nullcontext(compiler), display=Mock(),
                         Markdown=Mock(), Code=Mock(), Image=Mock(),
                         observation=Mock(return_value={"image_path": None, "compile": {
                             "outcome": "validation_failed", "diagnostic": "Exact output cannot compile",
                         }}), evaluate_pair=Mock())
        with tempfile.TemporaryDirectory() as folder:
            namespace["run_dir"] = Path(folder)
            exec(self.code["tikz-predict"], namespace)
            path = namespace["predictions_path"]
            original = path.read_bytes()
            rows = [json.loads(line) for line in original.decode().splitlines()]
            self.assertEqual(len(rows), 3)
            namespace["generate_tikz"].assert_has_calls([
                call(namespace["dataset"][task]["validation"][0], task) for task in namespace["tasks"]
            ])
            ipython_display = types.ModuleType("IPython.display")
            for name in ("Code", "Image", "Markdown", "display"):
                setattr(ipython_display, name, namespace[name])
            with patch.dict("sys.modules", {"IPython.display": ipython_display}):
                exec(self.code["tikz-inference-preview"], namespace)
            self.assertEqual([call.args[0] for call in namespace["observation"].call_args_list],
                             [row["output_tikz"] for row in rows])
            self.assertTrue(all(call.kwargs["preview"] for call in namespace["observation"].call_args_list))
            for row in rows:
                namespace["Code"].assert_any_call(row["output_tikz"], language="latex")
            namespace["display"].assert_any_call({
                "outcome": "validation_failed", "diagnostic": "Exact output cannot compile",
            })
            batch = types.ModuleType("evaluation.batch")
            batch.evaluate_file = Mock(return_value={"status": "completed_with_errors"})
            namespace["export_predictions"] = Mock(side_effect=AssertionError("Must reuse saved inference"))
            with patch.dict("sys.modules", {"evaluation.batch": batch}):
                exec(self.code["tikz-evaluate"], namespace)
            self.assertEqual(batch.evaluate_file.call_args.args,
                             (path, Path(folder) / "scores-validation.jsonl"))
            namespace["export_predictions"].assert_not_called()
            self.assertEqual(namespace["generate_tikz"].call_count, 3)
            self.assertEqual(path.read_bytes(), original)

    def test_optional_reload_uses_saved_adapter_without_creating_another_lora(self):
        vision = Mock()
        vision.from_pretrained.return_value = (Mock(), Mock())
        namespace = {"FastVisionModel": vision, "hf_model_id": "owner/saved-adapter", "max_seq_length": 4096}
        exec(self.code["unsloth-reload"], namespace)
        vision.from_pretrained.assert_not_called()
        tree = ast.parse(self.code["unsloth-reload"])
        tree.body[0].test = ast.Constant(value=True)
        unsloth = types.ModuleType("unsloth"); unsloth.FastVisionModel = vision
        with patch.dict("sys.modules", {"unsloth": unsloth, "torch": types.ModuleType("torch")}):
            exec(compile(ast.fix_missing_locations(tree), "reload-cell", "exec"), namespace)
        vision.from_pretrained.assert_called_once_with(
            model_name="owner/saved-adapter", max_seq_length=4096, load_in_4bit=False,
        )
        vision.for_inference.assert_called_once_with(namespace["model"])
        vision.get_peft_model.assert_not_called()

    def test_python_cells_parse_without_gpu_execution(self):
        for cell in self.cells:
            if cell["cell_type"] == "code":
                source = "".join(cell["source"])
                if source.startswith("%%"):
                    continue
                source = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("%"))
                compile(source, str(NOTEBOOK), "exec")
        self.assertTrue(all(not c.get("outputs") and c.get("execution_count") is None
                            for c in self.cells if c["cell_type"] == "code"))


if __name__ == "__main__":
    unittest.main()
