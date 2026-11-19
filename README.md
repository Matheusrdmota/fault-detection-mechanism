# Towards an Unsupervised Fault Detection Mechanism in Microservices

[![DOI](https://zenodo.org/badge/1229291444.svg)](https://doi.org/10.5281/zenodo.23382272)

## About

This repository contains the research artifacts associated with the paper *"Towards an Unsupervised Fault Detection Mechanism in Microservices."*

The project implements a fault detection mechanism for microservices using unsupervised machine learning techniques applied to system-collected metrics. The proposed approach aims to identify fault-related behavior in microservices through the analysis of system metrics.

The repository provides access to the implementation, experimental results, and data analysis notebook associated with the study. These artifacts are intended to support the inspection of the implementation, the examination of the experimental data, and the analysis of the results reported in the paper.

## Related Publication

This artifact is associated with the following research paper:

**Title:** Towards an Unsupervised Fault Detection Mechanism in Microservices

**Authors:**
- Matheus Rodrigues Mota (UFC, Brazil)
- Valéria Lelli (UFC, Brazil)
- Ismayle Santos (UECE, Brazil)
- Francisco Silva (UFC, Brazil)

**Venue:** Brazilian Symposium on Software Quality (SBQS 2026).

**Publication Status:** Accepted for publication.

**DOI:** Not yet available.

The paper has been accepted for publication at SBQS 2026.
The DOI and publication link will be added once the
official proceedings become available.

## Project Structure

```text
.
├── src/
│   ├── main.py
│   ├── config/
│   ├── detector/
│   └── external/
├── results/
│   ├── cpu_experiments_results_svm.csv
│   ├── cpu_experiments_results.csv
│   ├── memory_leak_experiments_results_svm.csv
│   ├── memory_leak_experiments_results.csv
│   ├── long_response_time_results.csv
│   ├── network_fault_detection_results.csv
│   └── fault_detector_analysis.ipynb
├── requirements.txt
├── chaos.yaml
├── README.md
└── .gitignore
```

The main directories and files are organized as follows:

- `src/`: contains the source code and supporting components of the fault detection mechanism.
- `src/main.py`: provides the main entry point for running the application.
- `src/config/`: contains configuration components.
- `src/detector/`: contains components related to fault detection.
- `src/external/`: contains supporting components that interact with external resources.
- `results/`: contains the experimental spreadsheets and the Jupyter Notebook used for data analysis.
- `requirements.txt`: lists the Python dependencies required by the project.

## Requirements

The following software is required:

- Python 3.10 or later
- pip
- The Python dependencies listed in `requirements.txt`

Additional services or infrastructure may be required depending on the configuration and execution scenario.

## Installation

Clone the repository:

```bash
git clone https://github.com/Matheusrdmota/fault-detection-mechanism.git
cd fault-detection-mechanism
```

Create and activate a virtual environment.

### Linux and macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Running the Application

From the repository root directory, run:

```bash
python -m src.main
```

Before execution, ensure that the required configuration files, input data, and external dependencies are available and properly configured.

The exact execution behavior may depend on the selected configuration and the external resources required by the implementation.

## Experimental Results and Data Analysis

The `results/` directory contains the experimental spreadsheets and the Jupyter Notebook used for the data analysis associated with the paper.

The spreadsheets contain information about the experimental executions, while the notebook documents the analysis performed on the experimental data.

To inspect the experimental results and execute the analysis:

1. Navigate to the `results/` directory.
2. Open the Jupyter Notebook in a compatible environment.
3. Ensure that the experimental spreadsheets are available in the locations expected by the notebook.
4. Install any additional notebook dependencies, if required.
5. Execute the notebook cells in sequence.

The notebook can be opened using Jupyter Notebook or JupyterLab. If Jupyter is not installed, it can be installed with:

```bash
pip install notebook
```

Then, from the repository root directory, run:

```bash
jupyter notebook
```

Open the notebook located in the `results/` directory.

The notebook and spreadsheets allow readers to inspect the experimental data and examine the analyses supporting the results reported in the paper.

## Technologies

The project uses the following technologies:

- **Python:** implementation of the fault detection mechanism and supporting components.
- **Machine learning libraries:** dependencies specified in `requirements.txt`.
- **Jupyter Notebook:** analysis of the experimental results.

The exact library versions and dependencies are documented in `requirements.txt`.

## Artifact Availability

The source code, experimental datasets, and data analysis
notebook associated with this research are publicly available
in Zenodo.

**Version-specific DOI (Version 2.0):**
https://doi.org/10.5281/zenodo.23382496

**Concept DOI:**
https://doi.org/10.5281/zenodo.23382272

The version-specific DOI identifies the exact artifact
version associated with the accepted research paper.

## Citation

If you use this artifact or its experimental results
in your research, please cite the associated paper
and the research artifact.

**Research Paper**

Matheus Rodrigues Mota, Valéria Lelli, Ismayle Santos,
and Francisco Silva. "Towards an Unsupervised Fault
Detection Mechanism in Microservices." Accepted for
publication at the Brazilian Symposium on Software
Quality (SBQS 2026).

**Research Artifact**

Matheus Rodrigues Mota, Valéria Lelli, Ismayle Santos,
and Francisco Silva. "Towards an Unsupervised Fault
Detection Mechanism in Microservices: Research Artifact."
Zenodo, version 2.0.

https://doi.org/10.5281/zenodo.23382496

## License

This artifact is distributed under different licenses
according to its components:

- **Source Code:** The source code and fault injection
  scripts are licensed under the MIT License.
  See the `LICENSE` file.

- **Experimental Data:** The experimental datasets,
  including CSV files, are licensed under the Creative
  Commons Attribution 4.0 International License (CC BY 4.0).
  See the `LICENSE-DATA` file.

- **Data Analysis Notebook:** Licensed under the
  Creative Commons Attribution 4.0 International License
  (CC BY 4.0).

Copyright (c) 2026 Matheus Rodrigues Mota,
Valéria Lelli, Ismayle Santos, and Francisco Silva.