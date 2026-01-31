# Polymarket Collector & Analyzer

Interactive menu-driven application for collecting and analyzing Polymarket trading activity.

## Features

### Data Collection
- Fetch complete trading history from Polymarket wallets
- Automatic pagination and deduplication
- Export to organized CSV files (grouped by market)
- Support for unlimited wallets

### Cyclic Collection
- Automated repeated data collection at regular intervals
- Configure custom intervals (e.g., every 1, 5, 10 minutes)
- Set number of cycles (e.g., 10, 50, 100 runs)
- Automatic data merging: Markets found in multiple cycles are combined
- Duplicate removal: Transactions are deduplicated across cycles
- Progress tracking: Live countdown and cycle status
- Summary reports: Detailed cycle statistics

### Visualization
- Interactive market analysis plots
- Trade scatter plot (price vs time, point size = USDC amount)
- Cumulative contract accumulation over time
- Automatic statistics calculation
- Quality filter: Markets with <30 trades are skipped

## Requirements

- Python 3.10+
- Network access to Polymarket API

## Installation

```bash
# Clone or copy the project
cd mcollect_clean

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure wallets
cp wallets.example.txt wallets.txt
# Edit wallets.txt with your wallet addresses
```

## Configuration

### Wallet Configuration

Edit `wallets.txt` in the format:
```
name,address
myWallet,0x1234567890abcdef...
trader1,0xabcdef1234567890...
```

### Application Settings

Edit these variables in `collector.py`:

| Variable | Description |
|----------|-------------|
| `WALLET_FILE` | Path to wallet configuration |
| `OUTPUT_ROOT` | CSV output directory |
| `PLOTS_DIR` | Plot output directory |
| `CYCLES_DIR` | Cyclic collection output |

## Usage

### Start the Application

```bash
python3 collector.py
```

### Main Menu

```
POLYMARKET COLLECTOR & ANALYZER

[1] Run Wallet Analysis
[2] Add New Wallet
[3] Create Market Plot
[4] Exit
```

### Wallet Analysis Modes

**[1] Single Run**: Collect data once, save to CSV files

**[2] Cyclic Collection**: Repeat at configured intervals
- Set interval (minutes between cycles)
- Set number of cycles
- Results automatically merged

### Creating Plots

1. Select blogger (data folder)
2. Select market (CSV file)
3. Generate dual plot (scatter + accumulation)

## Project Structure

```
mcollect_clean/
├── collector.py          # Main application
├── wallets.txt           # Wallet addresses (name,address)
├── wallets.example.txt   # Example wallet configuration
├── requirements.txt      # Python dependencies
├── README.md             # This documentation
├── LICENSE               # MIT License
├── .gitignore            # Git ignore rules
├── data/                 # Single run output
│   └── {wallet_name}/
│       └── {market_slug}.csv
├── cycles/               # Cyclic collection output
│   └── {wallet}_{timestamp}/
│       ├── cycle_001/
│       ├── cycle_002/
│       ├── merged/       # Combined results
│       └── summary.txt
└── plots/                # Generated charts
    └── {market_slug}.png
```

## CSV Data Format

| Field | Description |
|-------|-------------|
| `timestamp` | Unix timestamp |
| `datetime` | Human-readable time (UTC) |
| `type` | Activity type (TRADE, MERGE, SPLIT) |
| `outcome` | Trade side (Up/Down) |
| `size` | Number of contracts |
| `usdcSize` | Trade size in USDC |
| `price` | Contract price (0.01-0.99) |
| `transactionHash` | Blockchain tx hash |
| `title` | Market question |
| `slug` | Market identifier |

## Plot Features

### Top Panel - Purchase Scatter
- X-axis: Timestamp
- Y-axis: Price (0-1)
- Point size: Proportional to USDC amount
- Green = UP trades, Red = DOWN trades

### Bottom Panel - Contract Accumulation
- X-axis: Timestamp
- Y-axis: Cumulative contracts
- Green line = UP, Red line = DOWN

### Statistics Box
- Total trades
- UP/DOWN: trades, contracts, USDC spent

## Example Workflows

### Basic Analysis

```bash
# 1. Start application
python3 collector.py

# 2. Add wallet (if needed)
[2] Add New Wallet -> Enter name & address

# 3. Run single analysis
[1] Run Wallet Analysis -> Select wallet -> [1] Single Run

# 4. Create visualization
[3] Create Market Plot -> Select data -> Select market
```

### Live Monitoring Session

```bash
# 1. Start cyclic collection
[1] Run Wallet Analysis
Select wallet -> [2] Cyclic Collection

# 2. Configure
Interval: 1 minute
Cycles: 60 (= 1 hour total)

# 3. Review results
Check: cycles/{wallet}_{timestamp}/merged/
```

## API Details

- **Endpoint**: `https://data-api.polymarket.com/activity`
- **Rate Limiting**: 0.5s delay between requests (built-in)
- **Max Records**: 10,000 per wallet (configurable)
- **Pagination**: Automatic handling

## Troubleshooting

### No data collected
- Verify wallet address starts with 0x
- Check internet connection
- Wallet may have no trading activity

### Plot creation fails
- Ensure CSV contains TRADE records
- Verify matplotlib installation
- Check data integrity

### Cyclic collection issues
- Start with small values (1 min × 10 cycles)
- Data from completed cycles is saved even if interrupted
- Markets appearing only once are not merged

## Notes

- All timestamps in UTC
- CSV encoding: UTF-8
- Plot format: PNG, 150 DPI
- Minimum 30 trades required for market to be saved

## License

MIT License - see LICENSE file

## Support

For issues:
1. Check CSV files in `data/` directory
2. Review plots in `plots/` directory
3. Check console output for errors

---

**Built for Polymarket traders and analysts**
