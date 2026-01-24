# Asymmetric

CLI-first investment research workstation for value investing.

## Features

- SEC EDGAR integration with defensive rate limiting
- Piotroski F-Score calculation
- (Coming soon) Altman Z-Score, AI analysis with Gemini

## Setup

```bash
# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your SEC_IDENTITY

# Run tests
poetry run pytest
```

## Usage

```bash
# Run CLI
poetry run asymmetric --help
```
