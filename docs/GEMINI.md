## Project Overview

This project, "Netopo," is a network topology and configuration analysis tool. It is designed to ingest structured network device configuration data (JSON/XML), validate it against YANG models, and load it into a Neo4j graph database. The ultimate goal is to provide a platform for analyzing network state, understanding dependencies, and assessing the impact of configuration changes.

The project is a Python-based modular monolith. It uses a pluggable loader system to handle different network vendors and operating systems. The core of the system is a Neo4j graph database that serves as a versioned source of truth for the network topology and configuration.

**Key Technologies:**

*   **Backend:** Python 3.11+
*   **Data Validation:** `yangson`, `xmltodict`
*   **Database:** Neo4j
*   **API:** FastAPI
*   **CLI:** Click
*   **Testing:** pytest

## Building and Running

The project is in its early stages, and specific run commands are not yet finalized. However, based on the project plan, the following commands are anticipated:

**Installation:**

```bash
# TODO: Finalize dependency management (e.g., poetry, pip)
# pip install -r requirements.txt 
```

**Running the application (conceptual):**

```bash
# Load data from files into the graph
netopo-cli load --dir data/configs/

# Analyze the impact of a proposed change
netopo-cli analyze --device core-sw-01 --file proposed-changes/core-sw-01.json
```

**Running tests:**

```bash
pytest
```

## Development Conventions

*   **Code Style:** The project has not yet specified a code style, but it is recommended to use a standard Python formatter like `black` or `ruff`.
*   **Testing:** Unit tests are expected for each data loader plugin. A comprehensive library of test fixtures should be maintained.
*   **Versioning:** The project follows a phased development approach. The graph database will use a temporal versioning pattern.
*   **Contributions:** The project uses a standard forking workflow for contributions.
