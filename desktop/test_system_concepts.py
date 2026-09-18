"""Small, static catalog tests. No VM, shell exercises, UI or progress access."""

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

import system_concepts as catalog


ROOT = Path(__file__).resolve().parent


def _literal_assignment(filename, name):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"Missing static assignment: {filename}:{name}")


def _source_questions(drafts):
    for draft in drafts:
        if "cards" in draft:
            for card in draft["cards"]:
                yield from card["questions"]
        else:
            yield from draft["questions"]


class SystemConceptCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.drafts = catalog._read_drafts()
        cls.linux = catalog.load_catalog("linux")
        cls.docker = catalog.load_catalog("docker")
        cls.all = cls.linux + cls.docker
        cls.by_id = {q["id"]: q for q in cls.all}

    def test_counts_and_stable_ids(self):
        self.assertEqual((len(self.linux), len(self.docker)), (33, 11))
        self.assertEqual(len(self.by_id), 44)
        self.assertEqual(set(self.by_id), {q["id"] for q in _source_questions(self.drafts)})
        self.assertEqual(len({c["id"] for q in self.all for c in q["cards"]}), 33)

    def test_io_is_appended_without_changing_legacy_catalog(self):
        legacy_drafts = [d for d in self.drafts if d["kind"] not in {"io-concept-draft", "system-info-concept-draft"}]
        legacy = catalog._build_catalog(legacy_drafts)
        self.assertEqual(len(legacy), 32)
        self.assertEqual(self.linux[:21], [q for q in legacy if q["topic"] == "linux"])
        self.assertEqual(self.docker, [q for q in legacy if q["topic"] == "docker"])
        io_draft = next(d for d in self.drafts if d["kind"] == "io-concept-draft")
        self.assertEqual([q["id"] for q in self.linux[21:27]], [q["id"] for q in io_draft["questions"]])

    def test_system_is_appended_without_changing_the_existing_38_questions(self):
        legacy = catalog._build_catalog([d for d in self.drafts if d["kind"] != "system-info-concept-draft"])
        # Captured before this integration: covers IDs, text, choices, teaching,
        # sources, links and order, not just a current-vs-current comparison.
        # Later Docker 16–25 intentionally changes only these practice links.
        # Restore their exact old metadata solely for the immutable baseline check.
        from unittest.mock import patch
        old_routes = {
            "docker_attach_exec_lifetime": (("sim_exec", "sim_lifecycle"), "별도 명령 실행과 컨테이너 수명 관리를 다룹니다. 대화형 attach·detach와 주 셸 종료를 비교하는 실습은 별도입니다."),
            "docker_cpu_affinity_budget": (("sim_limits",), "CPU·메모리 제한 설정을 다룹니다. cpuset 설정, 실제 CPU 시간 측정이나 성능 비교는 여기서 평가하지 않습니다."),
            "docker_io_weight": ((), "현재 연결할 블록 I/O 가중치 적용·측정 실습은 없습니다. 지원되는 장치와 제어 기능 없이 실행 완료로 표시하지 않습니다."),
        }
        with patch.dict(catalog._PRACTICE, old_routes):
            previous = catalog._build_catalog([d for d in self.drafts if d["kind"] != "system-info-concept-draft"])
        digest = hashlib.sha256(json.dumps(previous, ensure_ascii=False, sort_keys=True,
                                          separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(digest, "94f5e41eb4baa552feb6dcfe3264c83e0b7958b6ad8d9777226f053e8b21b314")
        self.assertEqual(self.linux[:27], [q for q in legacy if q["topic"] == "linux"])
        self.assertEqual(self.docker, [q for q in legacy if q["topic"] == "docker"])
        draft = next(d for d in self.drafts if d["kind"] == "system-info-concept-draft")
        self.assertEqual([q["id"] for q in self.linux[27:]], [q["id"] for q in draft["questions"]])
        self.assertEqual((len(self.linux), len(self.docker), len(self.by_id)), (33, 11, 44))
        self.assertEqual(len({c["id"] for q in self.all for c in q["cards"]}), 33)

    def test_system_questions_keep_teaching_assumptions_feedback_and_sources(self):
        draft = next(d for d in self.drafts if d["kind"] == "system-info-concept-draft")
        concepts = {c["id"]: c for c in draft["concepts"]}
        self.assertEqual((len(draft["questions"]), len(concepts)), (6, 5))

        def leaves(value):
            if isinstance(value, dict):
                for child in value.values():
                    yield from leaves(child)
            elif isinstance(value, list):
                for child in value:
                    yield from leaves(child)
            else:
                yield str(value).rstrip("\n")

        for original in draft["questions"]:
            with self.subTest(question=original["id"]):
                actual = self.by_id[original["id"]]
                self.assertEqual(actual["topic"], "linux")
                self.assertEqual(actual["choices"], original["choices"])
                self.assertEqual(actual["answer"], original["answer"])
                self.assertEqual(actual["feedback"], original["choice_feedback"])
                self.assertEqual((len(actual["choices"]), len(actual["feedback"])), (4, 4))
                self.assertTrue(actual["prompt"].startswith(original["prompt"] + "\n\n가정 자료"))
                self.assertNotIn("```", actual["prompt"])
                self.assertNotIn("<br>", actual["prompt"])
                for value in leaves(original["scenario"]):
                    if value:
                        self.assertIn(value, actual["prompt"])
                self.assertEqual(actual["prerequisites"], original["prerequisites"])
                self.assertEqual([c["id"] for c in actual["cards"]], original["prerequisites"])
                for card in actual["cards"]:
                    source = concepts[card["id"]]
                    self.assertEqual(card["explanation"], "\n\n".join(source["explanation"]))
                    self.assertEqual(card["example"], source["example"])
                    self.assertNotIn(original["choices"][original["answer"]], card["example"])
                sources = {s["url"]: s["title"] for s in actual["sources"]}
                for sid in original["source_ids"]:
                    source = draft["sources"][sid]
                    self.assertEqual(sources[source["url"]], source["title"])
                self.assertFalse(actual["completion_equivalence"])
                self.assertFalse(actual["execution_completion"])
                self.assertEqual(json.loads(json.dumps(actual, ensure_ascii=False)), actual)

    def test_system_practice_links_do_not_claim_connectivity_rtc_ntp_or_snap_success(self):
        expected = {
            "system_info_uname_and_distribution": ["system_identity"],
            "system_info_hostname_is_not_dns_registration": ["system_identity"],
            "system_info_interface_up_is_not_connectivity": ["system_links", "system_addresses"],
            "system_info_epoch_does_not_shift_with_display_zone": ["system_time"],
            "system_info_rtc_missing_and_ntp_active": ["system_clock"],
            "system_info_snap_client_is_not_installed_application": [],
        }
        registered = {row[0] for row in _literal_assignment("system_course.py", "SPECS")}
        tree = ast.parse((ROOT / "mode_curriculum.py").read_text(encoding="utf-8"))
        self.assertTrue(any(isinstance(n, ast.ImportFrom) and n.module == "system_course" for n in ast.walk(tree)))
        for qid, keys in expected.items():
            question = self.by_id[qid]
            self.assertEqual(question["practice_keys"], keys)
            self.assertTrue(set(keys) <= registered)
            self.assertIn("자동 실행·채점·실습 완료 처리는 하지 않습니다", question["practice_note"])
        self.assertIn("DNS 등록·서비스 통신은 여기서 평가하지 않습니다", self.by_id["system_info_hostname_is_not_dns_registration"]["practice_note"])
        self.assertIn("통신 성공으로 처리하지 않습니다", self.by_id["system_info_interface_up_is_not_connectivity"]["practice_note"])
        self.assertIn("조사 완료가 RTC 읽기 성공이나 NTP 동기화 완료를 뜻하지 않습니다", self.by_id["system_info_rtc_missing_and_ntp_active"]["practice_note"])
        self.assertIn("실제 snap 설치·실행 실습은 없습니다", self.by_id["system_info_snap_client_is_not_installed_application"]["practice_note"])

    def test_system_draft_is_in_the_build_assets_without_execution(self):
        self.assertEqual(catalog._DRAFT_NAMES[-1], "system_info_concept_draft.json")
        build = (ROOT / "build.py").read_text(encoding="utf-8")
        self.assertIn("'--add-data', f'{root / \"python_teaching\" / \"system_info_concept_draft.json\"}:python_teaching'", build)
        # Parse only. Importing a UI test or build script would start unrelated work.
        ast.parse(build)
        ui_tests = ast.parse((ROOT / "test_system_concept_ui.py").read_text(encoding="utf-8"))
        self.assertTrue(any(isinstance(n, ast.FunctionDef) and n.name ==
                            "test_added_system_questions_render_grade_and_resume_without_running_lab"
                            for n in ast.walk(ui_tests)))

    def test_io_questions_preserve_teaching_and_assumptions(self):
        draft = next(d for d in self.drafts if d["kind"] == "io-concept-draft")
        concepts = {c["id"]: c for c in draft["concepts"]}

        def leaves(value):
            if isinstance(value, dict):
                for child in value.values():
                    yield from leaves(child)
            elif isinstance(value, list):
                for child in value:
                    yield from leaves(child)
            else:
                yield str(value).rstrip("\n")

        for original in draft["questions"]:
            with self.subTest(question=original["id"]):
                actual = self.by_id[original["id"]]
                self.assertEqual(actual["topic"], "linux")
                self.assertEqual(actual["choices"], original["choices"])
                self.assertEqual(actual["answer"], original["answer"])
                self.assertEqual(actual["feedback"], original["choice_feedback"])
                self.assertEqual((len(actual["choices"]), len(actual["feedback"])), (4, 4))
                self.assertTrue(actual["prompt"].startswith(original["prompt"] + "\n\n가정 자료"))
                for value in leaves(original["scenario"]):
                    if value:
                        self.assertIn(value, actual["prompt"])
                self.assertEqual(actual["prerequisites"], original["prerequisites"])
                for card in actual["cards"]:
                    self.assertEqual(set(card), {"id", "title", "explanation", "example"})
                    source = concepts[card["id"]]
                    self.assertEqual(card["explanation"], "\n\n".join(source["explanation"]))
                    self.assertEqual(card["example"], source["example"])
                self.assertTrue({draft["sources"][sid]["url"] for sid in original["source_ids"]} <=
                                {s["url"] for s in actual["sources"]})
                self.assertFalse(actual["completion_equivalence"])
                self.assertFalse(actual["execution_completion"])

    def test_io_practice_links_preserve_execution_boundary(self):
        expected = {
            "io_cat_append_and_finish_input": ["io_input"],
            "io_ctrl_d_depends_on_input_context": ["io_input", "io_pager"],
            "io_more_pipeline_reads_without_editing": ["io_pager"],
            "io_tree_hidden_directories_and_depth": ["io_tree"],
            "io_binary_copy_needs_execution_permission": ["io_binary"],
            "io_shebang_vs_explicit_interpreter": ["io_shebang"],
        }
        for qid, keys in expected.items():
            self.assertEqual(self.by_id[qid]["practice_keys"], keys)
            self.assertIn("자동 실행·채점·실습 완료 처리는 하지 않습니다", self.by_id[qid]["practice_note"])
        self.assertIn("셸을 Ctrl+D로 종료하는 것은", self.by_id["io_ctrl_d_depends_on_input_context"]["practice_note"])
        self.assertIn("fallback까지 실습으로 완료한 것은 아닙니다", self.by_id["io_shebang_vs_explicit_interpreter"]["practice_note"])

    def test_ui_shape_and_serialization(self):
        for q in self.all:
            with self.subTest(question=q["id"]):
                self.assertIn(q["topic"], ("linux", "docker"))
                self.assertTrue(q["title"] and q["prompt"] and q["practice_note"])
                self.assertEqual(len(q["choices"]), 4)
                self.assertEqual(len(q["feedback"]), 4)
                self.assertEqual(len(set(q["choices"])), 4)
                self.assertIs(type(q["answer"]), int)
                self.assertIn(q["answer"], range(4))
                self.assertFalse(q["completion_equivalence"])
                self.assertFalse(q["execution_completion"])
                self.assertIn("자동 실행·채점·실습 완료 처리는 하지 않습니다", q["practice_note"])
                self.assertEqual(q["prerequisites"], [c["id"] for c in q["cards"]])
                for card in q["cards"]:
                    self.assertEqual(set(card), {"id", "title", "explanation", "example"})
                    self.assertTrue(all(isinstance(v, str) and v for v in card.values()))
                self.assertTrue(q["sources"])
                for source in q["sources"]:
                    self.assertEqual(set(source), {"title", "url"})
                    self.assertTrue(source["title"])
                    self.assertTrue(source["url"].startswith(("https://", "desktop/")))
                    if source["url"].startswith("desktop/"):
                        self.assertIn("로컬", source["title"])
                        self.assertTrue((ROOT.parent / source["url"]).is_file())
        self.assertEqual(json.loads(json.dumps(self.all, ensure_ascii=False)), self.all)

    def test_original_assessment_is_unchanged(self):
        for original in _source_questions(self.drafts):
            actual = self.by_id[original["id"]]
            self.assertEqual(actual["choices"], original["choices"])
            self.assertEqual(actual["answer"], original["answer"])
            self.assertEqual(actual["feedback"], original["choice_feedback"])
            self.assertTrue(actual["prompt"].startswith(original["prompt"]))
        jobs = self.by_id["process_resume_pipeline_by_job_number"]["prompt"]
        self.assertIn("\n현재 셸의 작업 번호: 1\n", jobs)
        self.assertIn("\n프로세스 그룹 번호: 7300\n", jobs)
        self.assertIn("\n프로세스 번호 목록: 7300, 7301\n", jobs)

    def test_teaching_text_preserved_but_worked_answers_not_copied(self):
        source_cards = [c for d in self.drafts for c in d.get("cards", d.get("concepts", []))]
        normalized = {c["id"]: c for q in self.all for c in q["cards"]}
        for original in source_cards:
            expected = original["explanation"]
            if isinstance(expected, list):
                expected = "\n\n".join(expected)
            self.assertEqual(normalized[original["id"]]["explanation"], expected)
            self.assertNotEqual(normalized[original["id"]]["example"], original.get("worked_example"))
        self.assertNotIn("41 EA B0 80", normalized["linux_utf8"]["example"])
        self.assertNotIn("400", normalized["linux_process_threads"]["example"])

    def test_recursive_prerequisites_are_unique_and_first(self):
        q = self.by_id["docker_x11_display_not_permission"]
        self.assertEqual(q["prerequisites"], [
            "linux_components", "linux_process_threads", "docker_structure_oci",
            "docker_device_gpu_minimum", "docker_x11_authorization",
        ])
        for question in self.all:
            self.assertEqual(len(question["prerequisites"]), len(set(question["prerequisites"])))
        self.assertEqual(self.by_id["process_resume_pipeline_by_job_number"]["prerequisites"], [
            "process.thread_columns", "process.wait_stop", "process.shell_jobs",
        ])

    def test_scenario_tables_and_empty_arguments_are_visible(self):
        table = self.by_id["process_ps_uppercase_u_real_owner"]["prompt"]
        self.assertIn("관찰 자료\nPID   RUID  EUID", table)
        self.assertIn("5101  1100  0", table)
        self.assertIn("5102  0     1100", table)
        self.assertNotIn("```", table)
        self.assertNotIn("<br>", table)
        args = self.by_id["shell_forward_arguments_or_join_message"]["prompt"]
        self.assertIn('전달된 인자\n인자 1: "red blue"\n인자 2: ""', args)
        self.assertIn('인자 2: ""', args)
        self.assertIn('receiver "$@"', args)
        self.assertIn('receiver "$*"', args)
        source = self.by_id["shell_source_export_does_not_update_parent"]["prompt"]
        self.assertIn("준비된 파일\n파일 이름: setup.sh\nexport TEAM=green", source)
        self.assertIn("export TEAM=green\ncd /work/project", source)
        self.assertIn("각 비교는 독립적으로 시작합니다", source)
        cpu = self.by_id["process_time_is_cpu_not_elapsed"]["prompt"]
        self.assertIn("15분", cpu)
        self.assertIn("00:00:02", cpu)

    def test_every_scenario_value_survives_formatting(self):
        def leaves(value):
            if isinstance(value, dict):
                for child in value.values():
                    yield from leaves(child)
            elif isinstance(value, list):
                for child in value:
                    yield from leaves(child)
            else:
                yield str(value).rstrip("\n")

        for original in _source_questions(self.drafts):
            if "scenario" not in original:
                continue
            text = self.by_id[original["id"]]["prompt"]
            self.assertTrue(text.startswith(original["prompt"] + "\n\n가정 자료"))
            self.assertIn("문제에서 주어진 상황", text)
            for value in leaves(original["scenario"]):
                if value:
                    self.assertIn(value, text, original["id"])

    def test_sources_come_from_actual_draft_references(self):
        known = {v.get("url") or v.get("path") for d in self.drafts for v in d["sources"].values()}
        for q in self.all:
            urls = [s["url"] for s in q["sources"]]
            self.assertEqual(len(urls), len(set(urls)))
            self.assertTrue(set(urls) <= known)
        q = self.by_id["docker_x11_display_not_permission"]
        self.assertTrue(any("pthreads.7" in s["url"] for s in q["sources"]))
        self.assertTrue(any("Xsecurity.7" in s["url"] for s in q["sources"]))

    def test_practice_keys_are_current_registered_source_keys(self):
        # AST only: importing curriculum would pull in unrelated runtime/UI code.
        linux = set(_literal_assignment("linux_course.py", "LINUX_ORDER"))
        for filename in ("apt_course.py", "auth_course.py", "shell_course.py", "process_course.py", "io_course.py", "system_course.py"):
            linux.update(row[0] for row in _literal_assignment(filename, "SPECS"))
        sim = {"sim_" + row[0] for row in _literal_assignment("sim_lessons.py", "SPECS")}
        docker = (sim - linux) | {"docker_" + row[0] for row in _literal_assignment("docker_lessons.py", "SPECS")}
        for prefix in ("docker_sessions", "docker_runtime"):
            docker.update(prefix + '_' + row[0] for row in _literal_assignment(prefix + '_course.py', 'SPECS'))
        curriculum_tree = ast.parse((ROOT / "mode_curriculum.py").read_text(encoding="utf-8"))
        imported = {n.module for n in ast.walk(curriculum_tree) if isinstance(n, ast.ImportFrom)}
        self.assertTrue({"linux_course", "auth_course", "shell_course", "process_course", "io_course", "system_course", "docker_lessons"} <= imported)
        for q in self.all:
            self.assertTrue(set(q["practice_keys"]) <= {"linux": linux, "docker": docker}[q["topic"]], q["id"])
            self.assertEqual(len(q["practice_keys"]), len(set(q["practice_keys"])))

    def test_partial_practice_does_not_claim_expanded_completion(self):
        for qid in ("linux_components_posix_scope", "linux_setuid_effective_identity",
                    "docker_device_gpu_no_hardware",
                    "docker_device_gpu_least_privilege", "docker_x11_display_not_permission",
                    "docker_x11_window_not_gpu_proof"):
            self.assertEqual(self.by_id[qid]["practice_keys"], [])
        checks = {
            "shell_if_count_is_not_content_validation": "평가 범위가 아닙니다",
            "process_resume_pipeline_by_job_number": "여러 프로세스의 파이프라인",
            "process_ps_uppercase_u_real_owner": "실제·유효 UID가 같으므로",
            "docker_cpu_affinity_not_reservation": "cpuset",
            "linux_utf8_bytes_are_not_characters": "UTF-8 바이트",
        }
        for qid, text in checks.items():
            self.assertIn(text, self.by_id[qid]["practice_note"])
        self.assertEqual(self.by_id["shell_noclobber_expected_refusal"]["practice_keys"], ["shell_noclobber"])

    def test_new_docker_routes_only_link_executed_scope_not_hardware_success(self):
        expected = {
            'docker_attach_exec_main_process': ['docker_sessions_attach', 'docker_sessions_exec'],
            'docker_attach_exec_keep_service': ['docker_sessions_attach', 'docker_sessions_exec'],
            'docker_cpu_affinity_not_reservation': ['docker_runtime_stats', 'docker_runtime_cpu'],
            'docker_cpu_limit_is_ceiling': ['docker_runtime_stats', 'docker_runtime_cpu'],
            'docker_io_weight_not_throughput_promise': ['docker_runtime_io_weight'],
        }
        for key, routes in expected.items():
            row = self.by_id[key]
            self.assertEqual(row['practice_keys'], routes)
            self.assertFalse(row['execution_completion']); self.assertFalse(row['completion_equivalence'])
        self.assertIn('미측정', self.by_id['docker_io_weight_not_throughput_promise']['practice_note'])
        for key in ('docker_device_gpu_no_hardware', 'docker_x11_display_not_permission'):
            self.assertFalse(self.by_id[key]['practice_keys'])

    def test_duplicate_question_is_rejected_across_drafts(self):
        drafts = deepcopy(self.drafts)
        drafts[1]["questions"][0]["id"] = drafts[0]["cards"][0]["questions"][0]["id"]
        with self.assertRaisesRegex(ValueError, "Duplicate question ID"):
            catalog._build_catalog(drafts)

    def test_duplicate_concept_is_rejected(self):
        drafts = deepcopy(self.drafts)
        drafts[1]["concepts"].append(deepcopy(drafts[1]["concepts"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate concept ID"):
            catalog._build_catalog(drafts)

    def test_missing_prerequisite_and_cycle_are_rejected(self):
        for bad, message in (("not-a-concept", "Unknown prerequisite"), ("linux_components", "Cyclic prerequisites")):
            drafts = deepcopy(self.drafts)
            drafts[0]["cards"][0]["prerequisites"] = [bad]
            with self.assertRaisesRegex(ValueError, message):
                catalog._build_catalog(drafts)

    def test_missing_source_and_unknown_scenario_field_are_rejected(self):
        drafts = deepcopy(self.drafts)
        drafts[1]["questions"][0]["source_ids"] = ["unknown"]
        with self.assertRaisesRegex(ValueError, "Unknown source"):
            catalog._build_catalog(drafts)
        drafts = deepcopy(self.drafts)
        drafts[1]["questions"][0]["scenario"]["new_untranslated_field"] = "must not silently disappear"
        with self.assertRaisesRegex(ValueError, "Unformatted scenario field"):
            catalog._build_catalog(drafts)

    def test_invalid_choice_contract_is_rejected(self):
        for field, value in (("answer", True), ("answer", 4), ("choices", ["a"]), ("choice_feedback", ["why"] * 3)):
            drafts = deepcopy(self.drafts)
            drafts[1]["questions"][0][field] = value
            with self.assertRaisesRegex(ValueError, "Invalid four-choice question"):
                catalog._build_catalog(drafts)

    def test_invalid_topic_and_fresh_returns(self):
        for topic in ("Linux", "all", "ros", None):
            with self.assertRaises(ValueError):
                catalog.load_catalog(topic)
        first = catalog.load_catalog()
        first[0]["choices"][0] = "modified"
        first[0]["cards"][0]["explanation"] = "modified"
        self.assertEqual(catalog.load_catalog(), self.linux)

    def test_draft_files_not_changed_by_loading(self):
        paths = [catalog._DATA_DIR / name for name in catalog._DRAFT_NAMES]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        catalog.load_catalog("linux")
        catalog.load_catalog("docker")
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})


if __name__ == "__main__":
    unittest.main()
