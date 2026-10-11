import json
import tempfile
import random
import subprocess
from unittest.mock import patch
import unittest
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[2] / "train/Qwen3_5_(4B)_Vision.ipynb"


class TrainingInputsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cells = json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]
        cls.code = {
            tag: "".join(cell["source"])
            for cell in cls.cells if cell["cell_type"] == "code"
            for tag in cell.get("metadata", {}).get("tags", [])
        }
        cls.namespace = {}
        exec(cls.code["tikz-prompts"], cls.namespace)
        exec(cls.code["tikz-format"], cls.namespace)
        exec(cls.code["tikz-render"], cls.namespace)

    def sample(self, task, suffix=""):
        return {
            "id": "private-id" + suffix,
            "image": object() if task == "reconstruct" else None,
            "instruction": "A, B are distinct; M is the midpoint of AB." + suffix,
            "current_tikz": "\\begin{tikzpicture}\nBASE" + suffix + "\n\\end{tikzpicture}\n",
            "target_tikz": "\\begin{tikzpicture}\nTARGET" + suffix + "\n\\end{tikzpicture}\n",
        }

    def test_task_inputs_and_exact_target_are_separated(self):
        convert = self.namespace["convert_to_conversation"]
        for task in ("reconstruct", "generate", "edit"):
            with self.subTest(task=task):
                sample = self.sample(task)
                messages = convert(sample, task)["messages"]
                self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant"])
                self.assertEqual(messages[-1]["content"][0]["text"], sample["target_tikz"])
                user = messages[1]["content"]
                self.assertEqual(sum(item["type"] == "image" for item in user), int(task == "reconstruct"))
                inputs = "\n".join(item.get("text", "") for m in messages[:-1] for item in m["content"])
                self.assertNotIn(sample["target_tikz"], inputs)
                self.assertNotIn(sample["id"], inputs)
                if task == "reconstruct":
                    self.assertIs(user[1]["image"], sample["image"])
                    self.assertNotIn(sample["instruction"], inputs)
                else:
                    self.assertEqual(user[0]["text"], sample["instruction"])
                if task == "edit":
                    self.assertIn(sample["current_tikz"], inputs)
                else:
                    self.assertNotIn(sample["current_tikz"], inputs)

    def test_inference_uses_identical_prompt_without_requiring_target(self):
        convert = self.namespace["convert_to_conversation"]
        for task in ("reconstruct", "generate", "edit"):
            sample = self.sample(task)
            training = convert(sample, task)["messages"]
            sample.pop("target_tikz")
            self.assertEqual(convert(sample, task, include_target=False)["messages"], training[:-1])

    def test_missing_task_inputs_cannot_become_training_rows(self):
        convert = self.namespace["convert_to_conversation"]
        for task, field in (("reconstruct", "image"), ("generate", "instruction"),
                            ("edit", "current_tikz"), ("edit", "target_tikz")):
            sample = self.sample(task)
            sample[field] = None
            with self.subTest(task=task, field=field), self.assertRaises(ValueError):
                convert(sample, task)
        with self.assertRaises(ValueError):
            convert(self.sample("generate"), "unknown")

    def test_split_preparation_keeps_test_targets_out_of_training_and_validation(self):
        tasks = ("reconstruct", "generate", "edit")
        raw = {
            task: {split: [self.sample(task, ":" + split)] for split in ("train", "validation", "test")}
            for task in tasks
        }
        namespace = dict(self.namespace, TRAIN_TASKS=tasks, datasets_by_task=raw,
                         random=random, SEED=3407)
        exec(self.code["tikz-prepare"], namespace)
        self.assertEqual(len(namespace["train_dataset"]), 3)
        for row in namespace["train_dataset"]:
            self.assertIn(":train", row["messages"][-1]["content"][0]["text"])
        for task in tasks:
            self.assertIn(":validation", namespace["eval_datasets"][task][0]["messages"][-1]["content"][0]["text"])
            self.assertIs(namespace["test_datasets"][task], raw[task]["test"])

    def reviewed_export(self, folder, *, repeated_edit_start=False):
        import hashlib
        from PIL import Image
        from tools import draw_instruction as drawing

        rows = []
        tasks = ("reconstruct", "generate", "edit")
        for split_index, split in enumerate(("train", "validation", "test")):
            for task_index, task in enumerate(tasks):
                index = split_index * len(tasks) + task_index
                code = r"\begin{tikzpicture}\coordinate (A) at (%s,0);\end{tikzpicture}" % (20 + index)
                start = r"\begin{tikzpicture}\coordinate (A) at (%s,0);\end{tikzpicture}" % (10 if repeated_edit_start else index)
                png = Path(folder) / f"{index}.png"
                Image.new("RGB", (2, 2), (index, index, index)).save(png)
                png_hash = hashlib.sha256(png.read_bytes()).hexdigest()
                row = {
                    "id": f"fixture-{index}", "task": task.title(), "instruction": "Fixture geometry.",
                    "current_tikz": start if task == "edit" else None, "target_tikz": code,
                    "source": f"fixture:{split}", "source_group": f"family:{split}",
                    "provenance": {"parents": [f"parent:{split}"]}, "grade": 8,
                    "diagram_types": None, "split": split,
                    "rendered_png_path": str(png), "rendered_png_sha256": png_hash,
                    "rendered_tikz_sha256": hashlib.sha256(code.encode()).hexdigest(),
                    "verification": {"status": "ready", "reviewed_by": "test fixture"},
                }
                if task == "reconstruct":
                    row["image"] = {"path": str(png), "sha256": png_hash}
                row["verification"]["reviewed_input_sha256"] = drawing.review_digest(row)
                rows.append(row)
        directory = Path(folder) / "export"
        drawing.export_rows(rows, directory)
        return directory

    def load_export(self, directory):
        namespace = {"DATASET_DIR": directory, "TASKS": ("reconstruct", "generate", "edit"), "json": json}
        with patch("datasets.load_dataset", return_value={}):
            exec(self.code["tikz-load"], namespace)
        return namespace

    def test_notebook_loads_existing_reviewed_export_without_an_extra_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = self.reviewed_export(folder)
            namespace = self.load_export(directory)
            self.assertEqual(len(namespace["file_hashes"]), 9)
            self.assertEqual(len(namespace["DATASET_REVISION"]), 64)
            self.assertEqual(namespace["reviewers"], {"test fixture"})
            self.assertEqual(self.load_export(directory)["DATASET_REVISION"], namespace["DATASET_REVISION"])

    def test_notebook_rejects_changes_after_review(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        for field in ("instruction", "tikz_image", "split"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                directory = self.reviewed_export(folder)
                path = directory / "generate/train.parquet"
                table = pq.read_table(path)
                rows = table.to_pylist()
                rows[0][field] = ({"bytes": b"changed", "path": "changed.png"}
                                  if field == "tikz_image" else "changed")
                pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), path)
                with self.assertRaisesRegex(ValueError, "Changed reviewed input|Task/split mismatch"):
                    self.load_export(directory)

    def test_notebook_rejects_a_shared_edit_start_across_splits(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = self.reviewed_export(folder, repeated_edit_start=True)
            with self.assertRaisesRegex(ValueError, "duplicate crosses splits"):
                self.load_export(directory)

    def test_training_balances_task_exposure_without_changing_held_out_rows(self):
        tasks = ("reconstruct", "generate", "edit")
        raw = {task: {split: [self.sample(task, ":" + split)]
                      for split in ("train", "validation", "test")} for task in tasks}
        raw["edit"]["train"].append(self.sample("edit", ":train:second"))
        namespace = dict(self.namespace, TRAIN_TASKS=tasks, datasets_by_task=raw, random=random, SEED=3407)
        exec(self.code["tikz-prepare"], namespace)
        self.assertEqual(len(namespace["train_dataset"]), 6)
        for task in tasks:
            system = self.namespace["SYSTEM_PROMPTS"][task]
            self.assertEqual(sum(row["messages"][0]["content"][0]["text"] == system
                                 for row in namespace["train_dataset"]), 2)
            self.assertEqual(len(namespace["eval_datasets"][task]), 1)
            self.assertIs(namespace["test_datasets"][task], raw[task]["test"])

    def test_python_cells_parse_without_executing_gpu_work(self):
        for index, cell in enumerate(self.cells):
            source = "".join(cell["source"])
            if cell["cell_type"] == "code" and not source.startswith("%%"):
                with self.subTest(cell=index):
                    compile(source, f"{NOTEBOOK.name}:cell{index}", "exec")

    def test_preview_compiles_exact_source_renders_png_and_reuses_cached_result(self):
        render = self.namespace["render_tikz"]
        render.cache_clear()
        source = "\\usetikzlibrary{calc}\n\\begin{tikzpicture}\n% original source\n\\end{tikzpicture}\n"
        folders = []

        def run(command, **kwargs):
            folder = Path(kwargs["cwd"])
            folders.append(folder)
            if command[0] == "xelatex":
                document = (folder / "main.tex").read_text(encoding="utf-8")
                self.assertIn(source.strip(), document)
                self.assertIn("\\usepackage{tkz-euclide}", document)
                self.assertIn("-no-shell-escape", command)
                (folder / "main.pdf").write_bytes(b"test PDF")
            else:
                (folder / "preview.png").write_bytes(b"test PNG bytes")
            return subprocess.CompletedProcess(command, 0, stdout="")

        with patch("shutil.which", return_value="/test/tool"), patch("subprocess.run", side_effect=run) as process:
            self.assertEqual(render(source), b"test PNG bytes")
            self.assertEqual(render(source), b"test PNG bytes")
            self.assertEqual(process.call_count, 2)
        self.assertTrue(all(not folder.exists() for folder in folders))

    def test_preview_preserves_compiler_and_raster_failure_diagnostics(self):
        render = self.namespace["render_tikz"]
        for failing_tool in ("xelatex", "pdftoppm"):
            with self.subTest(tool=failing_tool):
                render.cache_clear()
                def run(command, **kwargs):
                    if command[0] == failing_tool:
                        return subprocess.CompletedProcess(command, 1, stdout="Concrete compiler diagnostic")
                    (Path(kwargs["cwd"]) / "main.pdf").write_bytes(b"test PDF")
                    return subprocess.CompletedProcess(command, 0, stdout="")
                with patch("shutil.which", return_value="/test/tool"), patch("subprocess.run", side_effect=run):
                    with self.assertRaisesRegex(RuntimeError, "Concrete compiler diagnostic"):
                        render("\\begin{tikzpicture}\\end{tikzpicture}")

    def test_preview_requires_colab_tools_and_propagates_timeout(self):
        render = self.namespace["render_tikz"]
        render.cache_clear()
        source = "\\begin{tikzpicture}\\end{tikzpicture}"
        with patch("shutil.which", return_value=None), patch("subprocess.run") as process:
            with self.assertRaisesRegex(RuntimeError, "Colab LaTeX setup"):
                render(source)
            process.assert_not_called()
        with patch("shutil.which", return_value="/test/tool"), patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("xelatex", 60)
        ):
            with self.assertRaises(subprocess.TimeoutExpired):
                render(source)


    def export_namespace(self, tasks=("reconstruct", "edit")):
        namespace = dict(
            self.namespace, json=json, Path=Path, RUN_FULL_INFERENCE=False,
            TRAIN_TASKS=tasks, DATASET_ID="fixture", DATASET_REVISION="frozen-revision",
            SEED=3407, MAX_NEW_TOKENS=4096,
            datasets_by_task={
                task: {"test": [self.sample(task, ":first"), self.sample(task, ":second")]}
                for task in tasks
            },
        )
        # Geo3K image hashes are not unique row keys.
        for task in tasks:
            for sample in namespace["datasets_by_task"][task]["test"]:
                sample["id"] = "same-image-hash"
        exec(self.code["tikz-export"], namespace)
        return namespace

    def test_full_inference_export_preserves_all_rows_and_exact_code(self):
        namespace = self.export_namespace()
        calls = []
        def generate(sample, task):
            messages = namespace["convert_to_conversation"](sample, task, include_target=False)["messages"]
            self.assertEqual([message["role"] for message in messages], ["system", "user"])
            calls.append((task, sample))
            return "% exact generated text\n" + sample["current_tikz"]
        namespace["generate_tikz"] = generate
        with self.namespace["tempfile"].TemporaryDirectory() as folder:
            destination = Path(folder) / "predictions.jsonl"
            namespace["export_predictions"](destination, "test")
            rows = [json.loads(line) for line in destination.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 4)
            self.assertEqual([(row["task"], row["row_index"]) for row in rows],
                             [("reconstruct", 0), ("reconstruct", 1), ("edit", 0), ("edit", 1)])
            for row, (task, sample) in zip(rows, calls):
                self.assertEqual(row["target_tikz"], sample["target_tikz"])
                self.assertEqual(row["output_tikz"], "% exact generated text\n" + sample["current_tikz"])
                self.assertEqual(row["dataset_revision"], "frozen-revision")
                self.assertEqual(row["arm"], "joint_sft")
                self.assertEqual(row["seed"], 3407)
                self.assertEqual(row["generation"], {"do_sample": False, "max_new_tokens": 4096})
            with self.assertRaises(FileExistsError):
                namespace["export_predictions"](destination, "test")
            self.assertEqual(len(calls), 4)
            with self.assertRaises(ValueError):
                namespace["export_predictions"](Path(folder) / "train.jsonl", "train")

    def test_inference_error_keeps_already_saved_predictions(self):
        namespace = self.export_namespace(tasks=("edit",))
        calls = []
        def generate(sample, task):
            calls.append(sample)
            if len(calls) == 2:
                raise RuntimeError("GPU interrupted")
            return "first generated result"
        namespace["generate_tikz"] = generate
        with self.namespace["tempfile"].TemporaryDirectory() as folder:
            destination = Path(folder) / "predictions.jsonl"
            with self.assertRaisesRegex(RuntimeError, "GPU interrupted"):
                namespace["export_predictions"](destination, "test")
            rows = [json.loads(line) for line in destination.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["row_index"], 0)
            self.assertEqual(rows[0]["output_tikz"], "first generated result")



    def test_unknown_experiment_arm_fails_before_generating(self):
        namespace = self.export_namespace()
        calls = []
        namespace["generate_tikz"] = lambda *args: calls.append(args)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "predictions.jsonl"
            with self.assertRaisesRegex(ValueError, "experiment arm"):
                namespace["export_predictions"](destination, "test", arm="unknown")
            self.assertFalse(destination.exists())
            self.assertEqual(calls, [])

    def test_base_and_adapter_use_the_same_rows_and_decoding_budget(self):
        namespace = self.export_namespace(tasks=("generate", "edit"))
        seen = []
        namespace["generate_tikz"] = lambda sample, task: seen.append((task, sample["instruction"])) or "tikz"
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            namespace["export_predictions"](directory / "base.jsonl", "test", arm="base")
            namespace["export_predictions"](directory / "joint.jsonl", "test", arm="joint_sft")
            base = [json.loads(line) for line in (directory / "base.jsonl").read_text().splitlines()]
            joint = [json.loads(line) for line in (directory / "joint.jsonl").read_text().splitlines()]
            self.assertEqual(seen[:4], seen[4:])
            for original, tuned in zip(base, joint):
                self.assertEqual(original.pop("arm"), "base")
                self.assertEqual(tuned.pop("arm"), "joint_sft")
                self.assertEqual(original, tuned)

if __name__ == "__main__":
    unittest.main()
