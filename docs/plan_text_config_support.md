ddread# Implementation Plan: Text-Based Configuration Analysis

**Objective:** Enhance the `netopo analyze config` command to accept raw text configuration files (e.g., from a `show running-config` command) in addition to the currently supported YANG-modeled JSON/XML.

**Core Strategy:** We will implement a modular, **rules-driven parsing engine**. This engine will use external, OS-specific YAML files to define the regex patterns required for parsing. This approach keeps the parsing rules separate from the application code, making the system highly maintainable and extensible. The final output will be a standard YANG-modeled JSON object, ensuring seamless integration with the existing analysis pipeline.

---

## Phase 1: Core Parsing & Transformation Engine

This phase focuses on building the standalone components required to convert text to a validated, YANG-modeled dictionary.

#### Task 1.1: Add New Dependencies
*   **Action:** Add `ciscoconfparse2` and `PyYAML` to the project's dependencies.
*   **File Action:** Modify `pyproject.toml`.

#### Task 1.2: Design and Create Parser Rule Files
*   **Action:** Create a new directory and the initial YAML rule files that will define the parsing logic.
*   **File Action (New Files):**
    *   Create directory: `src/parsing/rules/`
    *   Create new file: `src/parsing/rules/cisco_ios.yml`
    *   Create new file: `src/parsing/rules/arista_eos.yml`

#### Task 1.3: Implement the Rules-Driven Text Parser
*   **Action:** Create a generic "rules engine" class that loads a YAML rule file and uses its contents to drive `ciscoconfparse2`.
*   **File Action (New File):**
    *   Create new file: `src/parsing/text_parser.py`

#### Task 1.4: Implement the YANG Transformer Module
*   **Action:** Create a class responsible for transforming the structured data from the parser into the final YANG-modeled JSON format.
*   **File Action (New File):**
    *   Create new file: `src/parsing/config_transformer.py`

---

## Phase 2: Integration with the Application

This phase focuses on integrating the new parsing engine into the existing loader framework.

#### Task 2.1: Create the `TextLoader` Plugin
*   **Action:** Create a new loader class that inherits from `BaseLoader` and orchestrates the new text parser and transformer components.
*   **File Action (New File):**
    *   Create new file: `src/loaders/text_loader.py`

#### Task 2.2: Update the `LoaderFactory`
*   **Action:** Modify the existing loader factory to recognize text file extensions and dispatch them to the new `TextLoader`.
*   **File Action (Modify Existing):**
    *   Modify file: `src/loaders/loader_factory.py`

#### Task 2.3: Update the CLI (Minor)
*   **Action:** Update the CLI help text to inform users of the new capability.
*   **File Action (Modify Existing):**
    *   Modify file: `src/cli/main.py`

---

## Phase 3: Testing and Validation

This phase ensures the new feature is working correctly and is robust.

#### Task 3.1: Create Sample Data
*   **Action:** Add sample text configuration files to be used for testing.
*   **File Action (New Files):**
    *   Create new file: `tests/proposed-cisco-ios.txt`
    *   Create new file: `tests/proposed-arista-eos.txt`

#### Task 3.2: Write Unit Tests
*   **Action:** Create unit tests for the new parsing and transformation components.
*   **File Action (New Files):**
    *   Create new file: `tests/test_text_parser.py`
    *   Create new file: `tests/test_yang_transformer.py`

#### Task 3.3: Write an End-to-End Integration Test
*   **Action:** Create a new test file to validate the entire workflow from the CLI down to the analysis engine using a text file input.
*   **File Action (New File):**
    *   Create new file: `tests/test_cli_text_analysis.py`

---

## Summary of File Changes

### New Files to be Created:
*   `src/parsing/rules/cisco_ios.yml`
*   `src/parsing/rules/arista_eos.yml`
*   `src/parsing/text_parser.py`
*   `src/parsing/config_transformer.py`
*   `src/loaders/text_loader.py`
*   `tests/proposed-cisco-ios.txt`
*   `tests/proposed-arista-eos.txt`
*   `tests/test_text_parser.py`
*   `tests/test_yang_transformer.py`
*   `tests/test_cli_text_analysis.py`

### Existing Files to be Modified:
*   `pyproject.toml`
*   `src/loaders/loader_factory.py`
*   `src/cli/main.py`

---

## Progress Update: 2025-08-28

**Objective:** Assess and test the text-to-YANG conversion feature.

**Workflow:**
1.  **Assessment:** Reviewed the implementation of the text-to-YANG conversion feature, including the `TextParser`, `YangTransformer`, and YAML parsing rules.
2.  **Testing & Debugging:** Executed the existing unit tests (`tests/test_parser.py` and `tests/test_yang_transformer.py`) and identified several bugs related to static route parsing for Cisco IOS and BGP neighbor/OSPF area parsing for Arista EOS.
3.  **Bug Fixes:** Iteratively debugged and fixed the issues in the `ConfigTextParser`, `YangTransformer`, and the associated YAML rule files (`cisco_ios.yml`, `arista_eos.yml`).
4.  **End-to-End Testing:** Created a new end-to-end test file (`tests/test_cli_text_analysis.py`) to validate the entire text-to-YANG conversion workflow from the command line.

**Files Created:**
*   `tests/test_cli_text_analysis.py`: End-to-end test for the text conversion feature.

**Files Modified:**
*   `src/parsing/text_parser.py`: Improved parsing logic for generic features and parent-child features.
*   `src/parsing/config_transformer.py`: Made the transformer more robust to handle different data structures from the parser.
*   `src/parsing/rules/cisco_ios.yml`: Corrected regex for static route parsing.
*   `src/parsing/rules/arista_eos.yml`: Corrected regex for OSPF area parsing.
*   `src/loaders/text_loader.py`: Implemented abstract methods from `BaseLoader`.
*   `tests/test_yang_transformer.py`: Temporarily added and then removed print statements for debugging.

**Outcome:** The text-to-YANG conversion feature is now functioning correctly and is covered by both unit and end-to-end tests.
