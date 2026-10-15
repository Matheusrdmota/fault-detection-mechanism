# Towards an Unsupervised Fault Detection Mechanism in Microservices

[![DOI](https://zenodo.org/badge/1229291444.svg)](https://doi.org/10.5281/zenodo.23382272)

## About

This repository contains the research artifacts associated with the paper *"Towards an Unsupervised Fault Detection Mechanism in Microservices."*

The project implements a fault detection mechanism for microservices using unsupervised machine learning techniques applied to system-collected metrics. The proposed approach aims to identify fault-related behavior in microservices through the analysis of system metrics.

The repository provides access to the implementation, experimental results, and data analysis notebook associated with the study. These artifacts are intended to support the inspection of the implementation, the examination of the experimental data, and the analysis of the results reported in the paper.

## Project Structure

```text
.
├── src/
│   ├── main.py
│   ├── config/
│   ├── detector/
│   └── external/
├── results/
│   ├── cpu_experimental_results_svm.csv
│   ├── cpu_experimental_results.csv
│   ├── memory_leak_experimental_results_svm.csv
│   ├── memory_leak_experimental_results.csv
│   └── data_analysis.ipynb
├── requirements.txt
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
cd <repository>
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

The source code, experimental spreadsheets, and data analysis notebook are publicly available through this repository.

The artifacts are archived in Zenodo and can be identified using the following DOI:

**DOI:** [10.5281/zenodo.23382272](https://doi.org/10.5281/zenodo.23382272)

The repository provides the materials needed to inspect the implementation and experimental data and to examine the data analysis associated with the study.

## Citation

If you use or refer to these artifacts, please cite the associated research paper and the archived artifact record.

The artifact record is available at:

https://doi.org/10.5281/zenodo.23382272