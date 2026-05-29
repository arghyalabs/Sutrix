# Contributing to Scientific Data Orchestrator

Thank you for your interest in contributing to SDO! We welcome researchers, engineers, and data scientists to help improve this computational toxicology framework.

## Developer Onboarding

### Local Setup
1. Fork the repository and clone your fork.
2. Follow the `README.md` to set up your `.env` files.
3. Install backend dependencies via `pip install -r backend/requirements.txt`.
4. Install frontend dependencies via `npm ci` in the `frontend` folder.

### Git Flow
- Create a feature branch from `main` (e.g., `feature/add-new-descriptor`).
- Ensure your code passes all linting (`npm run lint` for frontend, `pytest` for backend).
- Submit a Pull Request targeting `main`.

### Code Style
- We strictly enforce type hints in Python (`typing` module).
- Frontend code must use TypeScript with strict mode enabled.
- Avoid committing large dataset files. Use the `data/` directory and `.gitignore` them.

## Bug Reports and Feature Requests
Please use the GitHub Issue tracker and fill out the provided templates.
