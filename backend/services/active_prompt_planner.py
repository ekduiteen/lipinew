from __future__ import annotations


def plan_active_collection_prompt(
    *,
    target_language: str,
    dominant_error_type: str,
    missing_domains: list[str],
    low_coverage_dialects: list[str],
    adapter_readiness: dict,
    teacher_profile: dict,
    teaching_mode: str,
) -> dict:
    del adapter_readiness, teacher_profile, teaching_mode

    instruction_map = {
        "word_boundary_error": (
            "word_boundary_probe",
            f"Please say one short natural household sentence in {target_language}. After I transcribe it, correct the word spacing if I join words incorrectly.",
        ),
        "halant_cluster_error": (
            "conjunct_probe",
            "Please say a few words with conjuncts or clusters, once slowly and once naturally.",
        ),
        "anusvara_chandrabindu_error": (
            "nasalization_probe",
            "Please say two nasalized minimal-pair words, first slowly and then normally.",
        ),
        "lexical_substitution": (
            "domain_vocabulary_probe",
            f"Please teach me a few {missing_domains[0] if missing_domains else 'daily life'} words in {target_language}, and correct me if I swap them for another language.",
        ),
        "wrong_language_detection": (
            "clean_target_probe",
            f"Please say one clean {target_language}-only phrase without mixing bridge languages.",
        ),
        "code_switch_misread": (
            "code_switch_probe",
            "Please say one mixed-language sentence and then tell me which words belong to which language.",
        ),
        "dialect_variant_marked_wrong": (
            "dialect_variant_probe",
            f"Please say a {low_coverage_dialects[0] if low_coverage_dialects else 'local'} variant and tell me if it is dialectal or a model mistake.",
        ),
    }
    next_prompt_type, instruction = instruction_map.get(
        dominant_error_type,
        ("general_probe", f"Please teach one short natural phrase in {target_language} and correct anything I get wrong."),
    )
    return {
        "next_prompt_type": next_prompt_type,
        "instruction": instruction,
        "suggested_teacher_instruction": instruction,
    }
